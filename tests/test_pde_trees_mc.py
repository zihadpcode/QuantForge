import numpy as np
import pytest

from quantforge import blackscholes as bs
from quantforge.exotics import down_barrier_call, geometric_asian
from quantforge.montecarlo import (
    asian_mc,
    barrier_mc,
    european_mc,
    gbm_paths,
    longstaff_schwartz,
)
from quantforge.pde import bs_pde
from quantforge.trees import binomial_price

# Longstaff & Schwartz (2001), Table 1, first row
LS = dict(S0=36.0, K=40.0, T=1.0, r=0.06, sigma=0.2)
AMERICAN_REF = 4.4866  # continuous exercise; PDE, LR and CRR agree on this to 3e-4


# ---------------------------------------------------------------- PDE --------
@pytest.mark.parametrize("is_call", [True, False])
@pytest.mark.parametrize("S0", [80.0, 100.0, 125.0])
def test_pde_european_matches_black_scholes(is_call, S0):
    res = bs_pde(S0, 100.0, 1.0, 0.05, 0.25, 0.02, is_call)
    g = bs.greeks(S0, 100.0, 1.0, 0.05, 0.25, 0.02, is_call)
    assert res.price == pytest.approx(g["price"], abs=1e-3)
    assert res.delta == pytest.approx(g["delta"], abs=1e-4)
    assert res.gamma == pytest.approx(g["gamma"], abs=1e-4)


def test_american_put_three_methods_agree():
    pde = bs_pde(LS["S0"], LS["K"], LS["T"], LS["r"], LS["sigma"], is_call=False, american=True).price
    lr = binomial_price(LS["S0"], LS["K"], LS["T"], LS["r"], LS["sigma"], is_call=False, american=True, n_steps=2001)
    crr = binomial_price(LS["S0"], LS["K"], LS["T"], LS["r"], LS["sigma"], is_call=False, american=True,
                         n_steps=2000, method="crr")
    for v in (pde, lr, crr):
        assert v == pytest.approx(AMERICAN_REF, abs=5e-4)
    euro = bs.price(LS["S0"], LS["K"], LS["T"], LS["r"], LS["sigma"], is_call=False)
    assert pde > euro + 0.6  # early exercise premium


def test_american_call_without_dividends_is_european():
    euro = bs.price(100, 100, 1, 0.05, 0.3)
    assert bs_pde(100, 100, 1, 0.05, 0.3, american=True).price == pytest.approx(euro, abs=2e-3)
    assert binomial_price(100, 100, 1, 0.05, 0.3, american=True, n_steps=1001) == pytest.approx(euro, abs=1e-3)


def test_american_call_with_dividends_exceeds_european():
    euro = bs.price(100, 100, 1, 0.02, 0.3, 0.08)
    pde = bs_pde(100, 100, 1, 0.02, 0.3, 0.08, american=True).price
    tree = binomial_price(100, 100, 1, 0.02, 0.3, 0.08, american=True, n_steps=2001)
    assert pde == pytest.approx(tree, abs=2e-3)
    assert pde > euro + 0.1


@pytest.mark.parametrize("K,H", [(100.0, 90.0), (90.0, 95.0)])
def test_barrier_pde_matches_closed_form(K, H):
    ref = down_barrier_call(100, K, H, 1.0, 0.05, 0.25, 0.02)
    assert bs_pde(100, K, 1.0, 0.05, 0.25, 0.02, lower_barrier=H).price == pytest.approx(ref, abs=1e-3)


def test_in_out_parity():
    out = down_barrier_call(100, 100, 90, 1, 0.05, 0.25, 0.02, "out")
    inn = down_barrier_call(100, 100, 90, 1, 0.05, 0.25, 0.02, "in")
    assert out + inn == pytest.approx(bs.price(100, 100, 1, 0.05, 0.25, 0.02), abs=1e-12)


# --------------------------------------------------------------- Trees -------
def test_leisen_reimer_european_accuracy():
    for K in (80.0, 100.0, 120.0):
        for cp in (True, False):
            ref = bs.price(100, K, 1, 0.05, 0.2, 0.01, cp)
            assert binomial_price(100, K, 1, 0.05, 0.2, 0.01, cp, n_steps=501) == pytest.approx(ref, abs=1e-4)


def test_bermudan_is_bracketed():
    args = (LS["S0"], LS["K"], LS["T"], LS["r"], LS["sigma"])
    euro = bs.price(*args, is_call=False)
    berm = binomial_price(*args, is_call=False, american=True, n_steps=4000, method="crr", exercise_dates=50)
    amer = binomial_price(*args, is_call=False, american=True, n_steps=4000, method="crr")
    assert euro < berm < amer
    assert berm == pytest.approx(4.478, abs=1e-3)  # LS (2001) finite-difference value, 50 dates


# ----------------------------------------------------------- Monte Carlo -----
def test_gbm_paths_moments():
    S = gbm_paths(100, 2.0, 0.05, 0.3, 0.01, n_steps=8, n_paths=200_000, seed=1)
    ST = S[:, -1]
    assert abs(ST.mean() - 100 * np.exp(0.04 * 2)) < 4 * ST.std() / np.sqrt(ST.size)
    lr = np.diff(np.log(S), axis=1)
    assert lr.std() == pytest.approx(0.3 * np.sqrt(0.25), rel=5e-3)


@pytest.mark.parametrize(
    "kw",
    [dict(), dict(antithetic=True), dict(control_variate=True), dict(antithetic=True, control_variate=True)],
)
def test_european_mc_is_unbiased(kw):
    ref = bs.price(100, 105, 1, 0.05, 0.2, 0.01)
    res = european_mc(100, 105, 1, 0.05, 0.2, 0.01, n_paths=200_000, seed=3, **kw)
    assert abs(res.price - ref) < 4 * res.stderr
    if kw.get("control_variate") and not kw.get("antithetic"):
        assert res.variance_reduction > 3
    if kw:
        # antithetics and the S_T control both remove the linear component of the
        # payoff, so their gains do not multiply - but each must still help
        assert res.variance_reduction > 1.5


def test_randomised_qmc_beats_mc():
    ref = bs.price(100, 100, 1, 0.05, 0.2)
    mc = european_mc(100, 100, 1, 0.05, 0.2, n_paths=2**16, seed=5)
    rqmc = european_mc(100, 100, 1, 0.05, 0.2, n_paths=2**16, seed=5, method="sobol")
    assert abs(rqmc.price - ref) < 4 * rqmc.stderr + 1e-4
    assert rqmc.stderr < mc.stderr / 10


def test_geometric_asian_closed_form_vs_mc():
    S = gbm_paths(100, 1, 0.05, 0.2, 0.0, 12, 400_000, seed=9)[:, 1:]
    pay = np.exp(-0.05) * np.maximum(np.exp(np.log(S).mean(axis=1)) - 100, 0)
    ref = geometric_asian(100, 100, 1, 0.05, 0.2, 0.0, 12)
    assert abs(pay.mean() - ref) < 4 * pay.std() / np.sqrt(pay.size)


def test_arithmetic_asian_control_variate():
    plain = asian_mc(100, 100, 1, 0.05, 0.2, 0, 52, n_paths=200_000, seed=4, control_variate=False)
    cv = asian_mc(100, 100, 1, 0.05, 0.2, 0, 52, n_paths=200_000, seed=4)
    assert cv.variance_reduction > 100
    assert abs(cv.price - plain.price) < 4 * plain.stderr
    assert cv.price > geometric_asian(100, 100, 1, 0.05, 0.2, 0.0, 52)  # AM >= GM


def test_barrier_brownian_bridge_removes_monitoring_bias():
    ref = down_barrier_call(100, 100, 90, 1, 0.05, 0.25, 0.02)
    bb = barrier_mc(100, 100, 90, 1, 0.05, 0.25, 0.02, n_steps=50, n_paths=200_000, seed=2)
    naive = barrier_mc(100, 100, 90, 1, 0.05, 0.25, 0.02, n_steps=50, n_paths=200_000, seed=2, brownian_bridge=False)
    assert abs(bb.price - ref) < 4 * bb.stderr
    assert naive.price - ref > 10 * naive.stderr  # discrete monitoring misses crossings


def test_longstaff_schwartz_matches_bermudan_lattice():
    args = (LS["S0"], LS["K"], LS["T"], LS["r"], LS["sigma"])
    berm = binomial_price(*args, is_call=False, american=True, n_steps=4000, method="crr", exercise_dates=50)
    res = longstaff_schwartz(*args, is_call=False, n_exercise=50, n_paths=100_000, seed=1)
    # out-of-sample LSM is a lower bound up to MC noise and must be close to the lattice value
    assert res.price < berm + 4 * res.stderr
    assert res.price > berm - 4 * res.stderr - 0.01
