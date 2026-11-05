import numpy as np
import pytest
from scipy import stats

from quantforge.garch import GarchParams, fit_garch, garch_variance, simulate_garch
from quantforge.portfolio import (
    efficient_frontier,
    ledoit_wolf,
    min_variance,
    risk_contributions,
    risk_parity,
    tangency,
)
from quantforge.rates import (
    CIR,
    Vasicek,
    bootstrap_par_curve,
    fit_nss,
    nss_yield,
    par_rates_from_discount,
)
from quantforge.risk import (
    backtest_var,
    christoffersen,
    cornish_fisher_var,
    historical_var_es,
    kupiec_pof,
    monte_carlo_var_es,
    normal_var_es,
    student_t_var_es,
)


# ------------------------------------------------------------------ rates ----
def _trapz_discount(r, dt):
    return np.exp(-dt * 0.5 * (r[:, 1:].sum(axis=1) + r[:, :-1].sum(axis=1)))


def test_bootstrap_round_trip():
    par = np.array([0.030, 0.032, 0.034, 0.035, 0.036, 0.037, 0.0375, 0.038, 0.0385, 0.039])
    for freq in (1, 2):
        t = np.arange(1, par.size + 1) / freq
        D = bootstrap_par_curve(t, par, freq)
        assert np.all(np.diff(D) < 0)
        np.testing.assert_allclose(par_rates_from_discount(D, freq), par, atol=1e-14)
    with pytest.raises(ValueError):
        bootstrap_par_curve([1, 3], [0.03, 0.04])


def test_nss_fit_recovers_curve():
    t = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30])
    true = (0.04, -0.02, 0.015, -0.01, 1.5, 9.0)
    params, rmse = fit_nss(t, nss_yield(t, *true))
    assert rmse < 1e-7
    np.testing.assert_allclose(nss_yield(t, *params), nss_yield(t, *true), atol=1e-7)


def test_vasicek_bond_monte_carlo_and_asymptote():
    v = Vasicek(0.5, 0.04, 0.02)
    D = _trapz_discount(v.simulate(0.03, 5.0, 250, 100_000, seed=1), 5.0 / 250)
    assert abs(D.mean() - v.zcb(0.03, 5.0)) < 4 * D.std() / np.sqrt(D.size)
    # long yield -> b - sigma^2 / (2 a^2)
    assert v.zero_yield(0.03, 1e4) == pytest.approx(0.04 - 0.02**2 / (2 * 0.5**2), abs=1e-5)


def test_vasicek_bond_option_jamshidian():
    v, r0, T, S, X = Vasicek(0.5, 0.04, 0.02), 0.03, 1.0, 3.0, 0.92
    r = v.simulate(r0, T, 100, 200_000, seed=2)
    pay = _trapz_discount(r, T / 100) * np.maximum(v.zcb(r[:, -1], S - T) - X, 0)
    assert abs(pay.mean() - v.zcb_option(r0, T, S, X)) < 4 * pay.std() / np.sqrt(pay.size)
    parity = v.zcb_option(r0, T, S, X, True) - v.zcb_option(r0, T, S, X, False)
    assert parity == pytest.approx(v.zcb(r0, S) - X * v.zcb(r0, T), abs=1e-14)


def test_cir_bond_monte_carlo():
    c = CIR(0.8, 0.05, 0.15)
    assert c.feller
    r = c.simulate(0.03, 5.0, 250, 100_000, seed=3)
    assert r.min() >= 0
    D = _trapz_discount(r, 5.0 / 250)
    assert abs(D.mean() - c.zcb(0.03, 5.0)) < 4 * D.std() / np.sqrt(D.size)


# ------------------------------------------------------------------- risk ----
def test_normal_var_es_textbook():
    var, es = normal_var_es(0.0, 1.0, 0.99)
    assert var == pytest.approx(2.326347874, abs=1e-8)
    assert es == pytest.approx(2.665214220, abs=1e-8)


def test_student_t_converges_to_normal_and_is_fatter():
    v_n, e_n = normal_var_es(0.0, 0.02, 0.99)
    v_t, e_t = student_t_var_es(0.0, 0.02, 1e6, 0.99)
    assert v_t == pytest.approx(v_n, rel=1e-4) and e_t == pytest.approx(e_n, rel=1e-4)
    v4, e4 = student_t_var_es(0.0, 0.02, 4, 0.99)
    assert e4 > e_n and e4 / v4 > e_n / v_n


def test_student_t_es_against_simulation():
    nu, sd = 5.0, 0.015
    x = stats.t.rvs(nu, size=2_000_000, random_state=1) * sd * np.sqrt((nu - 2) / nu)
    v, e = student_t_var_es(0.0, sd, nu, 0.975)
    hv, he = historical_var_es(x, 0.975)
    assert hv == pytest.approx(v, rel=5e-3) and he == pytest.approx(e, rel=5e-3)


def test_historical_and_cornish_fisher_on_gaussian_data():
    x = np.random.default_rng(0).normal(0.001, 0.02, 1_000_000)
    v, e = normal_var_es(0.001, 0.02, 0.99)
    hv, he = historical_var_es(x, 0.99)
    assert hv == pytest.approx(v, rel=5e-3) and he == pytest.approx(e, rel=5e-3)
    assert cornish_fisher_var(x, 0.99) == pytest.approx(v, rel=5e-3)


def test_monte_carlo_portfolio_var():
    mu = np.array([0.0005, 0.0003])
    cov = np.array([[0.0004, 0.00012], [0.00012, 0.0001]])
    w = np.array([0.6, 0.4])
    v, e = normal_var_es(w @ mu, np.sqrt(w @ cov @ w), 0.99)
    mv, me = monte_carlo_var_es(w, mu, cov, 0.99, n_sims=1_000_000, seed=5)
    assert mv == pytest.approx(v, rel=1e-2) and me == pytest.approx(e, rel=1e-2)


def test_kupiec_and_christoffersen():
    rng = np.random.default_rng(1)
    good = rng.random(2500) < 0.01
    assert kupiec_pof(good, 0.99)[1] > 0.05
    too_many = rng.random(2500) < 0.03
    assert kupiec_pof(too_many, 0.99)[1] < 1e-4
    clustered = np.zeros(2500, bool)
    for start in range(100, 2500, 500):
        clustered[start:start + 5] = True  # 25 exceptions in 5 clusters
    assert kupiec_pof(clustered, 0.99)[1] > 0.05  # right count ...
    assert christoffersen(clustered)[1] < 1e-4  # ... but not independent


def test_garch_var_passes_backtest_while_static_var_fails():
    p = GarchParams(0.0, 2e-6, 0.10, 0.88)
    r, s2 = simulate_garch(p, 4000, seed=3)
    _, z = normal_var_es(0.0, 1.0, 0.99)
    garch_var = stats.norm.ppf(0.99) * np.sqrt(s2)  # true conditional VaR
    static_var = np.full_like(r, stats.norm.ppf(0.99) * r.std())
    assert backtest_var(r, garch_var, 0.99).passes()
    assert not backtest_var(r, static_var, 0.99).passes()


# ------------------------------------------------------------------ garch ----
def test_garch_filter_matches_loop():
    eps = np.random.default_rng(0).standard_normal(500) * 0.01
    s2, nxt = garch_variance(eps, 1e-6, 0.07, 0.9, 1e-4)
    ref = [1e-4]
    for e in eps:
        ref.append(1e-6 + 0.07 * e * e + 0.9 * ref[-1])
    np.testing.assert_allclose(s2, ref[:-1], rtol=1e-12)
    assert nxt == pytest.approx(ref[-1], rel=1e-12)


def test_garch_mle_recovers_parameters():
    true = GarchParams(0.0003, 2e-6, 0.08, 0.90)
    r, _ = simulate_garch(true, 8000, seed=11)
    fit = fit_garch(r)
    for name in ("alpha", "beta"):
        assert abs(getattr(fit.params, name) - getattr(true, name)) < 4 * fit.stderr[name]
    assert fit.params.persistence < 1
    f = fit.forecast(5000)
    assert f[-1] == pytest.approx(fit.params.long_run_variance, rel=1e-6)
    assert f[0] == pytest.approx(fit.next_var)


# -------------------------------------------------------------- portfolio ----
@pytest.fixture
def market():
    rng = np.random.default_rng(42)
    A = rng.standard_normal((6, 6))
    cov = (A @ A.T / 6 + np.eye(6) * 0.5) * 0.01
    mu = np.array([0.05, 0.07, 0.06, 0.09, 0.04, 0.08])
    return mu, cov


def test_min_variance_and_tangency_closed_forms(market):
    mu, cov = market
    w = min_variance(cov)
    assert w.sum() == pytest.approx(1)
    # first-order condition: cov @ w is proportional to the ones vector
    g = cov @ w
    np.testing.assert_allclose(g, g.mean(), rtol=1e-10)
    t = tangency(mu, cov, rf=0.02)
    g = cov @ t
    np.testing.assert_allclose(g / (mu - 0.02), (g / (mu - 0.02)).mean(), rtol=1e-10)


def test_tangency_has_highest_sharpe_on_frontier(market):
    mu, cov = market
    rets, vols, W = efficient_frontier(mu, cov, 200)
    t = tangency(mu, cov, rf=0.02)
    sr_t = (t @ mu - 0.02) / np.sqrt(t @ cov @ t)
    assert np.all((rets - 0.02) / vols <= sr_t + 1e-12)
    np.testing.assert_allclose(W.sum(axis=1), 1)
    np.testing.assert_allclose(W @ mu, rets, atol=1e-12)
    assert vols.min() == pytest.approx(np.sqrt(min_variance(cov) @ cov @ min_variance(cov)), rel=1e-9)


def test_long_only_solutions(market):
    mu, cov = market
    for w in (min_variance(cov, True), tangency(mu, cov, 0.02, True)):
        assert w.min() >= 0 and w.sum() == pytest.approx(1)
    rets, vols, W = efficient_frontier(mu, cov, 15, long_only=True)
    assert np.all(W >= -1e-12) and np.all(np.diff(vols) >= -1e-9)
    # long-only optimum can never beat unconstrained
    sr = lambda w: (w @ mu - 0.02) / np.sqrt(w @ cov @ w)
    assert sr(tangency(mu, cov, 0.02, True)) <= sr(tangency(mu, cov, 0.02)) + 1e-12


def test_risk_parity_equalises_contributions(market):
    _, cov = market
    w = risk_parity(cov)
    np.testing.assert_allclose(risk_contributions(w, cov), 1 / 6, atol=1e-10)
    b = np.array([0.3, 0.2, 0.2, 0.1, 0.1, 0.1])
    np.testing.assert_allclose(risk_contributions(risk_parity(cov, b), cov), b, atol=1e-10)


def test_ledoit_wolf_matches_sklearn():
    sk = pytest.importorskip("sklearn.covariance")
    rng = np.random.default_rng(0)
    X = rng.standard_normal((60, 20)) @ rng.standard_normal((20, 20))
    est = sk.LedoitWolf().fit(X)
    cov, s = ledoit_wolf(X)
    assert s == pytest.approx(est.shrinkage_, abs=1e-12)
    np.testing.assert_allclose(cov, est.covariance_, atol=1e-12)


def test_tangency_rejects_rf_above_gmv_return():
    cov = np.array([[0.04, 0.018], [0.018, 0.09]])
    mu = np.array([0.05, 0.12])
    gmv = min_variance(cov)
    assert gmv @ mu < 0.07  # rf above the GMV return: the old code returned the minimum-Sharpe portfolio
    with pytest.raises(ValueError):
        tangency(mu, cov, rf=0.07)
    w = tangency(mu, cov, rf=0.02)
    assert (w @ mu - 0.02) / np.sqrt(w @ cov @ w) > 0
