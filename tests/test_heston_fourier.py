import numpy as np
import pytest

from quantforge import blackscholes as bs
from quantforge.fourier import bs_cf, cos_price, lewis_price
from quantforge.heston import HestonParams, calibrate_heston, heston_price, simulate_heston_qe

# Fang & Oosterlee (2008), Table for Heston, reference value 5.785155450
FO = HestonParams(v0=0.0175, kappa=1.5768, theta=0.0398, sigma=0.5751, rho=-0.5711)
FO_REF = 5.785155450


@pytest.mark.parametrize("T", [0.02, 0.5, 5.0])
def test_fourier_methods_reproduce_black_scholes(T):
    K = np.array([50, 80, 100, 120, 200.0])
    cf = bs_cf(T, 0.05, 0.25, 0.02)
    ref = bs.price(100, K, T, 0.05, 0.25, 0.02, True)
    np.testing.assert_allclose(cos_price(cf, 100, K, T, 0.05, 0.02, True), ref, atol=1e-10)
    np.testing.assert_allclose(lewis_price(cf, 100, K, T, 0.05, 0.02, True), ref, atol=1e-9)


@pytest.mark.parametrize("method", ["cos", "lewis"])
def test_heston_fang_oosterlee_benchmark(method):
    assert heston_price(FO, 100, 100, 1.0, 0.0, 0.0, True, method=method) == pytest.approx(FO_REF, abs=1e-7)


@pytest.mark.parametrize(
    "p",
    [FO, HestonParams(0.09, 3.0, 0.05, 0.3, 0.3), HestonParams(0.04, 1.0, 0.06, 0.8, -0.8)],
)
def test_cos_agrees_with_lewis(p):
    K = np.linspace(50, 200, 16)
    for T in (0.05, 0.5, 2.0):
        cos = heston_price(p, 100, K, T, 0.03, 0.01, False)
        lew = heston_price(p, 100, K, T, 0.03, 0.01, False, method="lewis")
        np.testing.assert_allclose(cos, lew, atol=1e-7)


def test_heston_put_call_parity():
    K = np.linspace(60, 160, 11)
    c = heston_price(FO, 100, K, 1.3, 0.04, 0.02, True)
    p = heston_price(FO, 100, K, 1.3, 0.04, 0.02, False)
    np.testing.assert_allclose(c - p, 100 * np.exp(-0.02 * 1.3) - K * np.exp(-0.04 * 1.3), atol=1e-10)


def test_heston_collapses_to_black_scholes():
    # v0 = theta and vanishing vol-of-vol => constant variance
    p = HestonParams(0.04, 2.0, 0.04, 1e-4, 0.0)
    K = np.array([80, 100, 120.0])
    np.testing.assert_allclose(heston_price(p, 100, K, 1.0, 0.03, 0.0), bs.price(100, K, 1.0, 0.03, 0.2), atol=1e-6)


def test_qe_monte_carlo_matches_semi_analytic():
    ST = simulate_heston_qe(FO, 100, 1.0, 0.0, 0.0, n_steps=100, n_paths=200_000, seed=7)
    for K in (80.0, 100.0, 120.0):
        pay = np.maximum(ST - K, 0)
        se = pay.std() / np.sqrt(pay.size)
        ref = heston_price(FO, 100, K, 1.0, 0.0, 0.0, True)
        assert abs(pay.mean() - ref) < 4 * se + 5e-3
    # martingale check on the discounted asset
    assert abs(ST.mean() - 100) < 4 * ST.std() / np.sqrt(ST.size) + 0.02


def test_calibration_recovers_parameters():
    S, r, q = 100.0, 0.03, 0.01
    true = HestonParams(0.03, 2.5, 0.05, 0.6, -0.7)
    T = np.array([0.1, 0.25, 0.5, 1.0, 2.0])
    K = np.linspace(70, 140, 15)
    KK, TT = np.meshgrid(K, T)
    cp = KK >= S * np.exp((r - q) * TT)
    px = heston_price(true, S, KK, TT, r, q, cp)
    res = calibrate_heston(S, r, q, KK, TT, px, cp, x0=HestonParams(0.04, 1.0, 0.04, 0.3, -0.3))
    assert res.success
    np.testing.assert_allclose(res.params.as_array(), true.as_array(), rtol=1e-5, atol=1e-6)
    assert res.iv_rmse < 1e-6
