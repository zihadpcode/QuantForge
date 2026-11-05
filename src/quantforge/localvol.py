"""Dupire local volatility from an implied-variance surface, and MC under it.

Gatheral's form of Dupire's equation in terms of total implied variance
``w(k, T)`` and log-moneyness ``k = ln(K / F_T)``::

    sigma_loc^2(k, T) = (dw/dT) / g(k, T)

    g = (1 - k w_k / (2 w))^2 - w_k^2 / 4 (1/w + 1/4) + w_kk / 2

The denominator is exactly Durrleman's butterfly function, so local variance
is finite and positive precisely when the surface is free of static arbitrage.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .svi import durrleman_g

__all__ = ["dupire_local_vol", "simulate_local_vol"]


def dupire_local_vol(w_fn: Callable, k, T, hk: float = 1e-4, hT: float = 1e-5):
    """Local volatility at log-moneyness ``k`` and time ``T``.

    ``w_fn(k, T)`` must accept broadcastable arrays. Derivatives use central
    differences (forward difference in ``T`` when ``T <= hT``).
    """
    k, T = np.broadcast_arrays(np.asarray(k, float), np.asarray(T, float))
    w0 = w_fn(k, T)
    wkp, wkm = w_fn(k + hk, T), w_fn(k - hk, T)
    dwk = (wkp - wkm) / (2 * hk)
    d2wk = (wkp - 2 * w0 + wkm) / (hk * hk)
    lo = np.maximum(T - hT, 0.0)
    dwT = (w_fn(k, T + hT) - w_fn(k, lo)) / (T + hT - lo)
    g = durrleman_g(w0, dwk, d2wk, k)
    with np.errstate(divide="ignore", invalid="ignore"):
        lv2 = dwT / g
    return np.sqrt(np.maximum(lv2, 0.0))


def simulate_local_vol(
    w_fn: Callable,
    S0: float,
    T: float,
    r: float,
    q: float = 0.0,
    n_steps: int = 200,
    n_paths: int = 100_000,
    seed: int | None = None,
    antithetic: bool = True,
):
    """Terminal prices under the Dupire local-vol diffusion (log-Euler scheme).

    The local vol is evaluated at the mid-point of each time step, which removes
    the ill-defined ``T = 0`` evaluation and is second-order in time for the
    deterministic part of the coefficient.
    """
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    half = n_paths // 2 if antithetic else n_paths
    x = np.zeros(2 * half if antithetic else n_paths)  # ln(S_t / F_t)
    for i in range(n_steps):
        t_mid = (i + 0.5) * dt
        z = rng.standard_normal(half)
        if antithetic:
            z = np.concatenate([z, -z])
        sig = dupire_local_vol(w_fn, x, t_mid)
        # d ln(S/F) = -sigma^2/2 dt + sigma dW  (forward is a martingale drift)
        x = x - 0.5 * sig * sig * dt + sig * np.sqrt(dt) * z
    return S0 * np.exp((r - q) * T) * np.exp(x)
