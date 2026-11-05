"""Black-Scholes-Merton analytics with continuous dividend yield.

All functions are vectorised: any argument may be a scalar or a NumPy array and
standard broadcasting rules apply. ``is_call`` may be a bool or a bool array.

Conventions
-----------
* ``T`` is time to expiry in years, ``r`` the continuously compounded risk-free
  rate, ``q`` the continuous dividend (or foreign) yield, ``sigma`` the
  annualised volatility.
* ``theta`` is the calendar-time derivative dV/dt (per year), i.e. the change in
  value as time passes with everything else fixed. It is usually negative for
  long options.
* ``vega``/``rho`` are per unit (not per 1%) change in sigma / r.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr

__all__ = [
    "norm_pdf",
    "norm_cdf",
    "d1_d2",
    "price",
    "black76",
    "greeks",
    "forward",
]

_SQRT_2PI = np.sqrt(2.0 * np.pi)


def norm_pdf(x):
    return np.exp(-0.5 * np.square(x)) / _SQRT_2PI


def norm_cdf(x):
    return ndtr(x)


def forward(S, T, r, q=0.0):
    """Forward price of the underlying for delivery at ``T``."""
    return np.asarray(S, dtype=float) * np.exp((np.asarray(r) - np.asarray(q)) * np.asarray(T))


def d1_d2(S, K, T, r, sigma, q=0.0):
    S, K, T, r, sigma, q = map(lambda a: np.asarray(a, dtype=float), (S, K, T, r, sigma, q))
    vol_sqrt_t = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def _sign(is_call):
    return np.where(np.asarray(is_call, dtype=bool), 1.0, -1.0)


def price(S, K, T, r, sigma, q=0.0, is_call=True):
    """Black-Scholes-Merton price of a European option.

    Handles the degenerate limits ``T -> 0`` and ``sigma -> 0`` by returning the
    discounted intrinsic value of the forward.
    """
    S, K, T, r, sigma, q = map(lambda a: np.asarray(a, dtype=float), (S, K, T, r, sigma, q))
    w = _sign(is_call)
    df_r, df_q = np.exp(-r * T), np.exp(-q * T)
    degenerate = (T <= 0) | (sigma <= 0)
    # Substitute harmless values in degenerate slots so no warnings/NaNs leak;
    # those slots are overwritten with the intrinsic value below.
    d1, d2 = d1_d2(S, K, np.where(degenerate, 1.0, T), r, np.where(degenerate, 1.0, sigma), q)
    live = w * (S * df_q * norm_cdf(w * d1) - K * df_r * norm_cdf(w * d2))
    intrinsic = np.maximum(w * (S * df_q - K * df_r), 0.0)
    out = np.where(degenerate, intrinsic, live)
    return out[()] if out.ndim == 0 else out


def black76(F, K, T, r, sigma, is_call=True):
    """Black (1976) price of an option on a forward/futures ``F``."""
    F, K, T, r, sigma = map(lambda a: np.asarray(a, dtype=float), (F, K, T, r, sigma))
    w = _sign(is_call)
    vol_sqrt_t = sigma * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * vol_sqrt_t**2) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    out = np.exp(-r * T) * w * (F * norm_cdf(w * d1) - K * norm_cdf(w * d2))
    return out[()] if out.ndim == 0 else out


def greeks(S, K, T, r, sigma, q=0.0, is_call=True):
    """Closed-form first and second order Greeks.

    Returns a dict with ``price, delta, gamma, vega, theta, rho, vanna, volga,
    charm, epsilon`` (epsilon = dV/dq).
    """
    S, K, T, r, sigma, q = map(lambda a: np.asarray(a, dtype=float), (S, K, T, r, sigma, q))
    w = _sign(is_call)
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    sqrt_t = np.sqrt(T)
    df_r, df_q = np.exp(-r * T), np.exp(-q * T)
    pdf_d1 = norm_pdf(d1)
    Nd1, Nd2 = norm_cdf(w * d1), norm_cdf(w * d2)

    px = w * (S * df_q * Nd1 - K * df_r * Nd2)
    delta = w * df_q * Nd1
    gamma = df_q * pdf_d1 / (S * sigma * sqrt_t)
    vega = S * df_q * pdf_d1 * sqrt_t
    theta = (
        -S * df_q * pdf_d1 * sigma / (2.0 * sqrt_t)
        - w * r * K * df_r * Nd2
        + w * q * S * df_q * Nd1
    )
    rho = w * K * T * df_r * Nd2
    epsilon = -w * S * T * df_q * Nd1
    vanna = -df_q * pdf_d1 * d2 / sigma
    volga = vega * d1 * d2 / sigma
    # charm = d(delta)/dt (calendar time)
    charm = w * q * df_q * Nd1 - df_q * pdf_d1 * (
        2.0 * (r - q) * T - d2 * sigma * sqrt_t
    ) / (2.0 * T * sigma * sqrt_t)

    out = dict(
        price=px,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
        rho=rho,
        epsilon=epsilon,
        vanna=vanna,
        volga=volga,
        charm=charm,
    )
    return {k: (v[()] if np.ndim(v) == 0 else v) for k, v in out.items()}
