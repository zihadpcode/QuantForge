import numpy as np
import pytest

from quantforge import blackscholes as bs
from quantforge.localvol import dupire_local_vol, simulate_local_vol
from quantforge.svi import (
    SSVI,
    RawSVI,
    SVISurface,
    butterfly_arbitrage,
    calendar_arbitrage,
    fit_raw_svi,
)

K_GRID = np.linspace(-1.5, 1.5, 601)


def test_raw_svi_fit_recovers_exact_smile():
    true = RawSVI(a=0.02, b=0.12, rho=-0.45, m=0.05, s=0.18)
    T = 0.75
    k = np.linspace(-0.8, 0.6, 25)
    iv = true.implied_vol(k, T)
    fit = fit_raw_svi(k, iv, T)
    assert fit.rmse_iv < 1e-8
    assert fit.butterfly_free
    np.testing.assert_allclose(fit.params.w(K_GRID), true.w(K_GRID), atol=1e-7)


def test_svi_derivatives_are_correct():
    p = RawSVI(0.01, 0.2, -0.3, 0.1, 0.25)
    k, h = np.linspace(-1, 1, 21), 1e-5
    np.testing.assert_allclose(p.dw(k), (p.w(k + h) - p.w(k - h)) / (2 * h), atol=1e-8)
    np.testing.assert_allclose(p.d2w(k), (p.dw(k + h) - p.dw(k - h)) / (2 * h), atol=1e-7)


def test_detects_butterfly_arbitrage_vogt_example():
    # Axel Vogt's SVI slice from Gatheral & Jacquier (2014): arbitrageable
    bad = RawSVI(a=-0.0410, b=0.1331, rho=0.3060, m=0.3586, s=0.4153)
    assert bad.g(K_GRID).min() < 0
    _, ok = butterfly_arbitrage(bad.w, K_GRID)
    assert not ok


def test_ssvi_is_arbitrage_free_under_gatheral_jacquier_conditions():
    s = SSVI.heston_like(v0=0.04, v_inf=0.06, kappa=2.0, rho=-0.7, eta=1.0, gamma=0.4)
    assert s.gatheral_jacquier_sufficient
    Ts = np.linspace(0.02, 5, 40)
    for T in Ts:
        _, ok = butterfly_arbitrage(lambda k: s.total_variance(k, T), K_GRID)
        assert ok
    _, cal_ok = calendar_arbitrage([lambda k, T=T: s.total_variance(k, T) for T in Ts], K_GRID)
    assert cal_ok


def test_calendar_check_detects_crossing():
    lo = RawSVI(0.04, 0.1, -0.5, 0.0, 0.2)
    hi = RawSVI(0.03, 0.1, -0.5, 0.0, 0.2)  # lower variance at a later date
    worst, ok = calendar_arbitrage([lo.w, hi.w], K_GRID)
    assert not ok and worst < 0


def test_svi_surface_interpolation():
    s1, s2 = RawSVI(0.01, 0.1, -0.4, 0.0, 0.2), RawSVI(0.04, 0.12, -0.4, 0.0, 0.25)
    surf = SVISurface([0.5, 1.0], [s1, s2])
    k = np.linspace(-0.5, 0.5, 11)
    np.testing.assert_allclose(surf.total_variance(k, 0.5), s1.w(k))
    np.testing.assert_allclose(surf.total_variance(k, 1.0), s2.w(k))
    np.testing.assert_allclose(surf.total_variance(k, 0.75), 0.5 * (s1.w(k) + s2.w(k)))
    np.testing.assert_allclose(surf.total_variance(k, 0.25), 0.5 * s1.w(k))
    np.testing.assert_allclose(surf.implied_vol(k, 2.0), surf.implied_vol(k, 1.0))  # flat extrapolation
    rep = surf.arbitrage_report()
    assert rep["calendar_free"] and all(rep["butterfly_free_by_slice"])


def test_local_vol_of_flat_surface_is_flat():
    lv = dupire_local_vol(lambda k, T: 0.3**2 * T + 0 * k, np.linspace(-1, 1, 9), 0.7)
    np.testing.assert_allclose(lv, 0.3, atol=1e-6)


def test_local_vol_of_term_structure_is_forward_vol():
    # w(T) = 0.04 T + 0.02 T^2  =>  sigma_loc^2 = dw/dT = 0.04 + 0.04 T
    lv = dupire_local_vol(lambda k, T: 0.04 * T + 0.02 * T**2 + 0 * k, 0.0, 1.5)
    assert lv == pytest.approx(np.sqrt(0.04 + 0.04 * 1.5), abs=1e-6)


def test_dupire_monte_carlo_reprices_the_surface():
    """End-to-end: implied surface -> Dupire local vol -> MC -> implied surface."""
    surf = SSVI.heston_like(v0=0.04, v_inf=0.06, kappa=2.0, rho=-0.7, eta=1.0, gamma=0.4)
    S0, r, q, T = 100.0, 0.03, 0.01, 1.0
    ST = simulate_local_vol(surf.total_variance, S0, T, r, q, n_steps=100, n_paths=100_000, seed=11)
    F = S0 * np.exp((r - q) * T)
    for K in (75.0, 90.0, 100.0, 110.0, 125.0):
        call = K >= F
        ref = bs.price(S0, K, T, r, surf.implied_vol(np.log(K / F), T), q, call)
        pay = np.exp(-r * T) * np.maximum((ST - K) if call else (K - ST), 0)
        se = pay.std() / np.sqrt(pay.size)
        assert abs(pay.mean() - ref) < 4 * se + 0.01, (K, pay.mean(), ref, se)
