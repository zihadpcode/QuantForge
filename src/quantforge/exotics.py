"""Closed-form prices for path-dependent options under Black-Scholes.

These serve both as products in their own right and as exact benchmarks /
control variates for the Monte Carlo engine.
"""

from __future__ import annotations

import numpy as np

from . import blackscholes as bs
from .blackscholes import norm_cdf as N

__all__ = ["geometric_asian", "down_barrier_call"]


def geometric_asian(S0, K, T, r, sigma, q=0.0, n_fix: int = 252, is_call=True):
    """Discretely monitored geometric-average Asian option (Kemna-Vorst).

    Fixings at ``t_i = i T / n``, ``i = 1..n``. ``ln G`` is Gaussian with

    * mean ``ln S0 + (r - q - sigma^2/2) T (n + 1) / (2n)``
    * variance ``sigma^2 T (n + 1)(2n + 1) / (6 n^2)``.
    """
    n = n_fix
    mu = np.log(S0) + (r - q - 0.5 * sigma**2) * T * (n + 1) / (2.0 * n)
    var = sigma**2 * T * (n + 1) * (2 * n + 1) / (6.0 * n * n)
    sd = np.sqrt(var)
    d2 = (mu - np.log(K)) / sd
    d1 = d2 + sd
    fwd_g = np.exp(mu + 0.5 * var)
    w = 1.0 if is_call else -1.0
    return float(np.exp(-r * T) * w * (fwd_g * N(w * d1) - K * N(w * d2)))


def down_barrier_call(S0, K, H, T, r, sigma, q=0.0, knock="out"):
    """Continuously monitored down-and-out / down-and-in call (no rebate).

    Merton (1973) / Reiner-Rubinstein (1991) formulas, valid for ``S0 > H``.
    """
    if S0 <= H:
        raise ValueError("requires S0 > H")
    sqt = sigma * np.sqrt(T)
    lam = (r - q + 0.5 * sigma**2) / sigma**2
    dfr, dfq = np.exp(-r * T), np.exp(-q * T)
    vanilla = bs.price(S0, K, T, r, sigma, q, True)
    if H <= K:
        y = np.log(H * H / (S0 * K)) / sqt + lam * sqt
        c_di = S0 * dfq * (H / S0) ** (2 * lam) * N(y) - K * dfr * (H / S0) ** (2 * lam - 2) * N(y - sqt)
        c_do = vanilla - c_di
    else:
        x1 = np.log(S0 / H) / sqt + lam * sqt
        y1 = np.log(H / S0) / sqt + lam * sqt
        c_do = (
            S0 * dfq * N(x1)
            - K * dfr * N(x1 - sqt)
            - S0 * dfq * (H / S0) ** (2 * lam) * N(y1)
            + K * dfr * (H / S0) ** (2 * lam - 2) * N(y1 - sqt)
        )
        c_di = vanilla - c_do
    return float(c_do if knock == "out" else c_di)
