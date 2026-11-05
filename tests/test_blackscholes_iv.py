import numpy as np
import pytest

from quantforge import blackscholes as bs
from quantforge.implied_vol import implied_vol


def test_textbook_values():
    # Hull, S=K=100, T=1, r=5%, sigma=20%
    assert bs.price(100, 100, 1, 0.05, 0.2) == pytest.approx(10.450583572185565, abs=1e-12)
    assert bs.price(100, 100, 1, 0.05, 0.2, is_call=False) == pytest.approx(5.573526022256971, abs=1e-12)


def test_put_call_parity_grid():
    rng = np.random.default_rng(0)
    S, K = rng.uniform(50, 150, 200), rng.uniform(50, 150, 200)
    T, r = rng.uniform(0.01, 5, 200), rng.uniform(-0.01, 0.1, 200)
    q, sig = rng.uniform(0, 0.05, 200), rng.uniform(0.05, 1.0, 200)
    c = bs.price(S, K, T, r, sig, q, True)
    p = bs.price(S, K, T, r, sig, q, False)
    np.testing.assert_allclose(c - p, S * np.exp(-q * T) - K * np.exp(-r * T), atol=1e-10)


def test_black76_consistency():
    S, K, T, r, q, sig = 100.0, 95.0, 0.7, 0.04, 0.015, 0.3
    F = S * np.exp((r - q) * T)
    for cp in (True, False):
        assert bs.black76(F, K, T, r, sig, cp) == pytest.approx(bs.price(S, K, T, r, sig, q, cp), abs=1e-12)


def test_degenerate_limits():
    assert bs.price(110, 100, 0.0, 0.05, 0.2) == pytest.approx(10.0)
    assert bs.price(90, 100, 0.0, 0.05, 0.2, is_call=False) == pytest.approx(10.0)
    # zero vol: discounted forward intrinsic
    assert bs.price(100, 90, 1.0, 0.05, 0.0) == pytest.approx(100 - 90 * np.exp(-0.05))


@pytest.mark.parametrize("is_call", [True, False])
def test_greeks_against_finite_differences(is_call):
    S, K, T, r, q, sig = 105.0, 100.0, 0.75, 0.03, 0.02, 0.25
    g = bs.greeks(S, K, T, r, sig, q, is_call)

    def P(S=S, K=K, T=T, r=r, sig=sig, q=q):
        return bs.price(S, K, T, r, sig, q, is_call)

    h = 1e-4
    assert g["delta"] == pytest.approx((P(S=S + h) - P(S=S - h)) / (2 * h), abs=1e-7)
    assert g["gamma"] == pytest.approx((P(S=S + 1e-2) - 2 * P() + P(S=S - 1e-2)) / 1e-4, abs=1e-6)
    assert g["vega"] == pytest.approx((P(sig=sig + h) - P(sig=sig - h)) / (2 * h), abs=1e-6)
    assert g["rho"] == pytest.approx((P(r=r + h) - P(r=r - h)) / (2 * h), abs=1e-6)
    assert g["epsilon"] == pytest.approx((P(q=q + h) - P(q=q - h)) / (2 * h), abs=1e-6)
    # theta is dV/dt = -dV/dT
    assert g["theta"] == pytest.approx(-(P(T=T + h) - P(T=T - h)) / (2 * h), abs=1e-6)

    def G(name, **kw):
        args = dict(S=S, K=K, T=T, r=r, sigma=sig, q=q, is_call=is_call)
        args.update(kw)
        return bs.greeks(**args)[name]

    assert g["vanna"] == pytest.approx((G("delta", sigma=sig + h) - G("delta", sigma=sig - h)) / (2 * h), abs=1e-6)
    assert g["volga"] == pytest.approx((G("vega", sigma=sig + h) - G("vega", sigma=sig - h)) / (2 * h), abs=1e-5)
    assert g["charm"] == pytest.approx(-(G("delta", T=T + h) - G("delta", T=T - h)) / (2 * h), abs=1e-6)


def test_implied_vol_round_trip_wide_grid():
    S, r, q = 100.0, 0.03, 0.01
    K = np.array([40, 60, 80, 90, 100, 110, 125, 150, 200, 300], float)
    T = np.array([0.01, 0.1, 0.5, 1, 3, 5], float)
    sig = np.array([0.05, 0.15, 0.3, 0.6, 1.0, 1.5])
    KK, TT, SS, CP = np.meshgrid(K, T, sig, [True, False], indexing="ij")
    px = bs.price(S, KK, TT, r, SS, q, CP)
    vega = bs.greeks(S, KK, TT, r, SS, q, CP)["vega"]
    iv = implied_vol(px, S, KK, TT, r, q, CP)
    # only test where the quote actually carries volatility information
    informative = vega > 1e-4
    assert informative.sum() > 500
    err = np.abs(iv - SS)[informative]
    assert np.all(np.isfinite(iv))
    assert err.max() < 1e-9
    # where the quote is well conditioned we are at machine precision
    assert np.abs(iv - SS)[vega > 1e-2].max() < 1e-11


def test_implied_vol_rejects_arbitrage_and_scalar():
    assert np.isnan(implied_vol(-1.0, 100, 100, 1, 0.0))
    assert np.isnan(implied_vol(101.0, 100, 100, 1, 0.0))  # call above spot
    assert np.isnan(implied_vol(1.0, 100, 50, 1, 0.0))  # call below intrinsic
    v = implied_vol(10.450583572185565, 100, 100, 1, 0.05)
    assert isinstance(v, float)
    assert v == pytest.approx(0.2, abs=1e-12)


def test_implied_vol_above_initial_bracket():
    # very short-dated quotes can need sigma >> 10; they used to be clamped to 10.0
    for sig, T in ((25.0, 1e-3), (500.0, 1e-4)):
        p = bs.price(100, 100, T, 0.0, sig)
        assert implied_vol(p, 100, 100, T, 0.0) == pytest.approx(sig, rel=1e-9)
