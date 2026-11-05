"""Robust, vectorised Black-Scholes implied volatility.

Algorithm
---------
1. Reject prices outside the no-arbitrage bounds (returns NaN).
2. Map every quote to its out-of-the-money equivalent via put-call parity. OTM
   prices carry no intrinsic value, which keeps the root-finding well
   conditioned for deep ITM quotes.
3. Run a *safeguarded* Newton iteration on every element simultaneously: each
   element keeps a bracket ``[lo, hi]`` that is guaranteed to contain the root
   (the BS price is strictly increasing in sigma). A Newton step that leaves the
   bracket, or a vanishing vega, falls back to bisection. This gives Newton's
   quadratic convergence where it is safe and bisection's guaranteed
   convergence everywhere else.
"""

from __future__ import annotations

import numpy as np

from . import blackscholes as bs

__all__ = ["implied_vol"]

_VOL_LO, _VOL_HI, _VOL_CAP = 1e-9, 10.0, 1e4


def implied_vol(
    price,
    S,
    K,
    T,
    r,
    q=0.0,
    is_call=True,
    tol=1e-12,
    max_iter=100,
):
    """Black-Scholes implied volatility.

    Parameters
    ----------
    price : array_like
        Option premium(s).
    tol : float
        Tolerance on the volatility: iteration stops once the Newton step
        ``|price error| / vega`` is below ``tol``, or once the price error is at
        floating-point resolution (``8 eps max(S, K)``).

    Returns
    -------
    ndarray or float
        Implied volatilities; NaN where the quote violates arbitrage bounds.
    """
    price, S, K, T, r, q = map(lambda a: np.asarray(a, dtype=float), (price, S, K, T, r, q))
    is_call = np.asarray(is_call, dtype=bool)
    price, S, K, T, r, q, is_call = np.broadcast_arrays(price, S, K, T, r, q, is_call)
    shape = price.shape
    price, S, K, T, r, q, is_call = (a.ravel().copy() for a in (price, S, K, T, r, q, is_call))

    df_r, df_q = np.exp(-r * T), np.exp(-q * T)
    fwd_value = S * df_q - K * df_r  # PV(F - K)

    # --- arbitrage bounds -------------------------------------------------
    lower = np.where(is_call, np.maximum(fwd_value, 0.0), np.maximum(-fwd_value, 0.0))
    upper = np.where(is_call, S * df_q, K * df_r)
    valid = (price >= lower - 1e-14 * K) & (price < upper) & (T > 0)

    # --- convert to OTM option -------------------------------------------
    otm_call = K * df_r >= S * df_q  # call is OTM when K >= F
    target_is_call = otm_call
    # price of the OTM option implied by parity
    otm_price = np.where(
        is_call == target_is_call,
        price,
        np.where(is_call, price - fwd_value, price + fwd_value),
    )
    otm_price = np.maximum(otm_price, 0.0)

    out = np.full(price.shape, np.nan)
    idx = np.flatnonzero(valid)
    if idx.size == 0:
        return out.reshape(shape)[()] if out.reshape(shape).ndim == 0 else out.reshape(shape)

    tgt = otm_price[idx]
    s_, k_, t_, r_, q_, c_ = S[idx], K[idx], T[idx], r[idx], q[idx], target_is_call[idx]

    # zero OTM price -> zero vol (degenerate but arbitrage-free)
    zero = tgt <= 0.0

    # Initial guess (Brenner-Subrahmanyam near ATM, Manaster-Koehler for wings)
    fwd = s_ * np.exp((r_ - q_) * t_)
    x = np.log(fwd / k_)
    mk = np.sqrt(2.0 * np.abs(x) / t_)
    brs = np.sqrt(2.0 * np.pi / t_) * tgt / (s_ * np.exp(-q_ * t_))
    sigma = np.clip(np.where(np.abs(x) < 0.1, brs, np.maximum(mk, brs)), 0.05, 3.0)

    lo = np.full_like(sigma, _VOL_LO)
    hi = np.full_like(sigma, _VOL_HI)
    # Every valid quote is below the sigma -> inf limit, so a root exists; widen the
    # bracket until it contains it (very short-dated quotes can need sigma >> 10).
    need = bs.price(s_, k_, t_, r_, hi, q_, c_) < tgt
    while need.any() and hi.max() < _VOL_CAP:
        hi[need] *= 2.0
        need = bs.price(s_, k_, t_, r_, hi, q_, c_) < tgt
    sigma = np.minimum(sigma, 0.5 * hi)
    price_floor = 8.0 * np.finfo(float).eps * np.maximum(s_, k_)
    done = zero.copy()

    for _ in range(max_iter):
        act = ~done
        if not act.any():
            break
        g = bs.greeks(s_[act], k_[act], t_[act], r_[act], sigma[act], q_[act], c_[act])
        diff = g["price"] - tgt[act]
        vega = g["vega"]

        with np.errstate(divide="ignore", invalid="ignore"):
            step = np.abs(diff) / vega
        converged = (step <= tol) | (np.abs(diff) <= price_floor[act])
        # update bracket
        too_high = diff > 0
        hi_a = np.where(too_high, sigma[act], hi[act])
        lo_a = np.where(too_high, lo[act], sigma[act])

        with np.errstate(divide="ignore", invalid="ignore"):
            newton = sigma[act] - diff / vega
        bad = ~np.isfinite(newton) | (newton <= lo_a) | (newton >= hi_a)
        new_sigma = np.where(bad, 0.5 * (lo_a + hi_a), newton)
        # bracket collapsed to machine precision -> accept
        collapsed = (hi_a - lo_a) <= 1e-15 * np.maximum(hi_a, 1.0)

        new_sigma = np.where(converged, sigma[act], new_sigma)
        sigma[act] = new_sigma
        lo[act], hi[act] = lo_a, hi_a
        done[act] = converged | collapsed

    # anything that failed to converge (e.g. root beyond _VOL_CAP) is reported as NaN
    final = bs.price(s_, k_, t_, r_, sigma, q_, c_) - tgt
    vega_f = bs.greeks(s_, k_, t_, r_, sigma, q_, c_)["vega"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ok = (np.abs(final) <= price_floor) | (np.abs(final) / vega_f <= max(tol, 1e-10) * 100)
    sigma[~ok & ~zero] = np.nan
    sigma[zero] = 0.0
    out[idx] = sigma
    out = out.reshape(shape)
    return out[()] if out.ndim == 0 else out
