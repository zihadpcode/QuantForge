"""Characteristic-function option pricing.

Two independent methods are provided so each can validate the other:

* :func:`cos_price` - the Fourier-cosine expansion of Fang & Oosterlee (2008).
  Exponential convergence in the number of terms for smooth densities; prices
  a whole strike strip with a single evaluation of the characteristic function.
* :func:`lewis_price` - Lewis (2001) single-integral formula evaluated with
  adaptive quadrature. Slow but very accurate; used as a reference.

A characteristic function here is any callable ``cf(u)`` returning
``E[exp(i u ln(S_T / S_0))]`` under the risk-neutral measure (i.e. including
the ``(r - q) T`` drift) and accepting complex arrays of any shape.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy import integrate

__all__ = ["bs_cf", "cumulants", "cos_price", "lewis_price"]

CharFn = Callable[[np.ndarray], np.ndarray]


def bs_cf(T: float, r: float, sigma: float, q: float = 0.0) -> CharFn:
    """Characteristic function of ln(S_T/S_0) under Black-Scholes."""

    def cf(u):
        u = np.asarray(u, dtype=complex)
        return np.exp(1j * u * (r - q - 0.5 * sigma**2) * T - 0.5 * sigma**2 * T * u**2)

    return cf


def cumulants(cf: CharFn, h: float = 1e-3) -> tuple[float, float]:
    """First two cumulants of ln(S_T/S_0) by central differences of ln cf.

    ``ln cf(u) = i c1 u - c2 u^2 / 2 + O(u^3)``. Using ``u = +-h`` cancels the odd
    (even) terms in the imaginary (real) part, giving O(h^2) accuracy.
    """
    lp, lm = np.log(cf(np.array(h))), np.log(cf(np.array(-h)))
    c1 = float((lp.imag - lm.imag) / (2.0 * h))
    c2 = float(-(lp.real + lm.real) / (h * h))
    return c1, c2


def cos_price(
    cf: CharFn,
    S: float,
    K,
    T: float,
    r: float,
    q: float = 0.0,
    is_call=True,
    N: int = 256,
    L: float = 12.0,
):
    """European option prices via the COS method.

    Puts are priced directly (bounded payoff -> stable) and calls obtained
    through put-call parity, as recommended by Fang & Oosterlee.

    Parameters
    ----------
    cf : callable
        Characteristic function of ln(S_T/S_0) for maturity ``T``.
    K : array_like
        Strike(s); all share maturity ``T``.
    N : int
        Number of cosine terms.
    L : float
        Truncation width in standard deviations of ln(S_T/S_0).
    """
    K = np.atleast_1d(np.asarray(K, dtype=float))
    is_call = np.broadcast_to(np.asarray(is_call, dtype=bool), K.shape)
    c1, c2 = cumulants(cf)
    width = L * np.sqrt(max(c2, 1e-12))

    x = np.log(S / K)  # (m,)
    # y = ln(S_T/K) = x + ln(S_T/S0) is centred at x + c1
    a = x + c1 - width
    b = x + c1 + width
    ba = b - a  # identical for all strikes
    k = np.arange(N)
    u = k * np.pi / ba[0]  # (N,)

    phi = cf(u)  # (N,)
    # e^{i u (x - a)} with x - a = width - c1, identical for all strikes
    kernel = (phi * np.exp(1j * u * (width - c1))).real  # (N,)

    # Put payoff K (1 - e^y) on [a, d] with d = min(b, 0)
    d = np.minimum(b, 0.0)[:, None]  # (m,1)
    a_ = a[:, None]
    uu = u[None, :]
    arg = uu * (d - a_)
    chi = (np.cos(arg) * np.exp(d) - np.exp(a_) + uu * np.sin(arg) * np.exp(d)) / (1.0 + uu**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        psi = np.where(k[None, :] == 0, d - a_, np.sin(arg) / np.where(uu == 0, 1.0, uu))
    Vk = (2.0 / ba[:, None]) * (psi - chi)
    Vk = np.where((a < 0.0)[:, None], Vk, 0.0)  # payoff identically 0 on [a,b] if a >= 0

    weights = np.ones(N)
    weights[0] = 0.5
    put = K * np.exp(-r * T) * (Vk * (kernel * weights)[None, :]).sum(axis=1)
    put = np.maximum(put, 0.0)
    call = put + S * np.exp(-q * T) - K * np.exp(-r * T)
    out = np.where(is_call, call, put)
    return out[0] if out.size == 1 else out


def lewis_price(cf: CharFn, S: float, K, T: float, r: float, q: float = 0.0, is_call=True):
    """European option prices from Lewis (2001)'s formula.

    ``C = S e^{-qT} - sqrt(S K) e^{-(r+q)T/2} / pi *
    int_0^inf Re[e^{i u k} phi_X(u - i/2)] / (u^2 + 1/4) du``

    with ``X = ln(S_T/S_0) - (r-q)T`` and ``k = ln(S/K) + (r-q)T``.
    """
    K = np.atleast_1d(np.asarray(K, dtype=float))
    is_call = np.broadcast_to(np.asarray(is_call, dtype=bool), K.shape)
    drift = (r - q) * T
    out = np.empty_like(K)
    for i, strike in enumerate(K):
        kk = np.log(S / strike) + drift

        def integrand(u, kk=kk):
            z = u - 0.5j
            phi_x = cf(np.array(z)) * np.exp(-1j * z * drift)
            return (np.exp(1j * u * kk) * phi_x).real / (u * u + 0.25)

        val, _ = integrate.quad(integrand, 0.0, np.inf, limit=500, epsabs=1e-13, epsrel=1e-11)
        call = S * np.exp(-q * T) - np.sqrt(S * strike) * np.exp(-(r + q) * T / 2.0) / np.pi * val
        out[i] = call if is_call[i] else call - S * np.exp(-q * T) + strike * np.exp(-r * T)
    return out[0] if out.size == 1 else out
