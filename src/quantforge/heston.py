"""Heston (1993) stochastic volatility model.

    dS_t = (r - q) S_t dt + sqrt(v_t) S_t dW^S_t
    dv_t = kappa (theta - v_t) dt + sigma sqrt(v_t) dW^v_t,   d<W^S, W^v> = rho dt

Provides
--------
* the characteristic function in the "little Heston trap" formulation of
  Albrecher et al. (2007), which is free of the branch-cut discontinuity of the
  original formula;
* fast pricing (COS) and reference pricing (Lewis quadrature);
* vega-weighted least-squares calibration to an option surface;
* path simulation with Andersen's (2008) Quadratic-Exponential (QE) scheme.
"""

from __future__ import annotations

from dataclasses import astuple, dataclass

import numpy as np
from scipy import optimize

from . import blackscholes as bs
from .fourier import cos_price, lewis_price
from .implied_vol import implied_vol

__all__ = [
    "HestonParams",
    "heston_cf",
    "heston_price",
    "calibrate_heston",
    "CalibrationResult",
    "simulate_heston_qe",
]


@dataclass(frozen=True)
class HestonParams:
    v0: float
    kappa: float
    theta: float
    sigma: float  # vol of variance
    rho: float

    @property
    def feller(self) -> float:
        """Feller ratio 2 kappa theta / sigma^2 (> 1 keeps v_t strictly positive)."""
        return 2.0 * self.kappa * self.theta / self.sigma**2

    def as_array(self) -> np.ndarray:
        return np.array(astuple(self), dtype=float)


def heston_cf(params: HestonParams, T: float, r: float, q: float = 0.0):
    """Characteristic function of ln(S_T/S_0) (Albrecher et al. form)."""
    v0, kappa, theta, sigma, rho = astuple(params)

    def cf(u):
        u = np.asarray(u, dtype=complex)
        iu = 1j * u
        beta = kappa - rho * sigma * iu
        d = np.sqrt(beta * beta + sigma**2 * (iu + u * u))
        g = (beta - d) / (beta + d)
        e = np.exp(-d * T)
        one_minus_ge = 1.0 - g * e
        C = (kappa * theta / sigma**2) * ((beta - d) * T - 2.0 * np.log(one_minus_ge / (1.0 - g)))
        D = ((beta - d) / sigma**2) * (1.0 - e) / one_minus_ge
        return np.exp(iu * (r - q) * T + C + D * v0)

    return cf


def heston_price(
    params: HestonParams,
    S: float,
    K,
    T,
    r: float,
    q: float = 0.0,
    is_call=True,
    method: str = "cos",
    N: int = 2048,
    L: float = 40.0,
):
    """European option prices under Heston.

    ``K``, ``T`` and ``is_call`` broadcast together; the strip for each distinct
    maturity is priced in one COS evaluation.

    The COS defaults (``L=40`` standard deviations, ``N=2048`` terms) are wider
    than the ``L=12`` usually quoted for Heston: when the Feller condition is
    badly violated the log-price density has fat exponential tails and a
    2-cumulant truncation range of 12 sd leaves errors of order 1e-3. With
    these defaults the method agrees with Lewis quadrature to ~1e-8 for typical
    equity parameters (cost: a few ms per maturity). For extreme dynamics
    (vol-of-vol ~1, Feller ratio << 1, multi-year maturities) increase ``L``
    and ``N`` together, e.g. ``L=100, N=16384``, or use ``method="lewis"``.
    """
    K, T, is_call = np.broadcast_arrays(
        np.asarray(K, dtype=float), np.asarray(T, dtype=float), np.asarray(is_call, dtype=bool)
    )
    out = np.empty(K.shape, dtype=float)
    for t in np.unique(T):
        m = T == t
        cf = heston_cf(params, float(t), r, q)
        if method == "cos":
            out[m] = cos_price(cf, S, K[m], float(t), r, q, is_call[m], N=N, L=L)
        elif method == "lewis":
            out[m] = lewis_price(cf, S, K[m], float(t), r, q, is_call[m])
        else:
            raise ValueError(f"unknown method {method!r}")
    return out[()] if out.ndim == 0 else out


@dataclass
class CalibrationResult:
    params: HestonParams
    iv_rmse: float  # root-mean-square implied vol error
    price_rmse: float
    n_quotes: int
    nfev: int
    success: bool


_LB = np.array([1e-4, 1e-3, 1e-4, 1e-2, -0.999])
_UB = np.array([1.0, 20.0, 1.0, 5.0, 0.999])


def calibrate_heston(
    S: float,
    r: float,
    q: float,
    strikes,
    maturities,
    market_prices,
    is_call=True,
    x0: HestonParams | None = None,
    n_starts: int = 1,
    seed: int = 0,
) -> CalibrationResult:
    """Calibrate Heston to option quotes by vega-weighted least squares.

    The residual ``(model - market) / vega_BS`` is a first-order approximation of
    the implied-volatility error, so the fit is effectively in IV space without
    paying for an IV inversion inside the optimiser. Trust-region reflective
    least squares handles the box constraints. Optional random restarts guard
    against the well-known flat directions of the Heston objective.
    """
    K, T, mkt, cp = np.broadcast_arrays(
        np.asarray(strikes, float),
        np.asarray(maturities, float),
        np.asarray(market_prices, float),
        np.asarray(is_call, bool),
    )
    K, T, mkt, cp = (a.ravel() for a in (K, T, mkt, cp))
    mkt_iv = implied_vol(mkt, S, K, T, r, q, cp)
    vega = bs.greeks(S, K, T, r, np.nan_to_num(mkt_iv, nan=0.2), q, cp)["vega"]
    w = 1.0 / np.maximum(vega, 1e-3 * S * np.sqrt(T))

    def resid(x):
        p = HestonParams(*x)
        return (heston_price(p, S, K, T, r, q, cp) - mkt) * w

    starts = [x0.as_array() if x0 is not None else np.array([0.04, 2.0, 0.04, 0.5, -0.5])]
    rng = np.random.default_rng(seed)
    for _ in range(max(n_starts - 1, 0)):
        starts.append(rng.uniform(_LB + 0.05 * (_UB - _LB), _UB - 0.5 * (_UB - _LB)))

    best = None
    for s0 in starts:
        sol = optimize.least_squares(
            resid, np.clip(s0, _LB, _UB), bounds=(_LB, _UB), method="trf",
            x_scale="jac", xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=2000,
        )
        if best is None or sol.cost < best.cost:
            best = sol

    p = HestonParams(*best.x)
    model = heston_price(p, S, K, T, r, q, cp)
    model_iv = implied_vol(model, S, K, T, r, q, cp)
    ok = np.isfinite(model_iv) & np.isfinite(mkt_iv)
    return CalibrationResult(
        params=p,
        iv_rmse=float(np.sqrt(np.mean((model_iv[ok] - mkt_iv[ok]) ** 2))),
        price_rmse=float(np.sqrt(np.mean((model - mkt) ** 2))),
        n_quotes=K.size,
        nfev=int(best.nfev),
        success=bool(best.success),
    )


def simulate_heston_qe(
    params: HestonParams,
    S0: float,
    T: float,
    r: float,
    q: float = 0.0,
    n_steps: int = 100,
    n_paths: int = 100_000,
    seed: int | None = None,
    psi_c: float = 1.5,
    return_paths: bool = False,
):
    """Simulate Heston paths with Andersen's QE scheme (central discretisation).

    Returns terminal prices ``S_T`` (and the full ``(n_steps+1, n_paths)`` arrays
    of S and v if ``return_paths``).
    """
    v0, kappa, theta, sigma, rho = astuple(params)
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    ekt = np.exp(-kappa * dt)
    g1 = g2 = 0.5
    K0 = -rho * kappa * theta * dt / sigma
    K1 = g1 * dt * (kappa * rho / sigma - 0.5) - rho / sigma
    K2 = g2 * dt * (kappa * rho / sigma - 0.5) + rho / sigma
    K3 = g1 * dt * (1.0 - rho**2)
    K4 = g2 * dt * (1.0 - rho**2)

    x = np.full(n_paths, np.log(S0))
    v = np.full(n_paths, v0)
    if return_paths:
        xs = np.empty((n_steps + 1, n_paths))
        vs = np.empty((n_steps + 1, n_paths))
        xs[0], vs[0] = x, v

    for i in range(n_steps):
        m = theta + (v - theta) * ekt
        s2 = v * sigma**2 * ekt / kappa * (1.0 - ekt) + theta * sigma**2 / (2.0 * kappa) * (1.0 - ekt) ** 2
        psi = s2 / (m * m)
        zv = rng.standard_normal(n_paths)
        uv = rng.random(n_paths)
        v_new = np.empty(n_paths)

        quad = psi <= psi_c
        if quad.any():
            ip = 1.0 / psi[quad]
            b2 = 2.0 * ip - 1.0 + np.sqrt(2.0 * ip) * np.sqrt(2.0 * ip - 1.0)
            a = m[quad] / (1.0 + b2)
            v_new[quad] = a * (np.sqrt(b2) + zv[quad]) ** 2
        exp_ = ~quad
        if exp_.any():
            p = (psi[exp_] - 1.0) / (psi[exp_] + 1.0)
            beta = (1.0 - p) / m[exp_]
            u = uv[exp_]
            v_new[exp_] = np.where(u <= p, 0.0, np.log((1.0 - p) / np.maximum(1.0 - u, 1e-300)) / beta)

        zs = rng.standard_normal(n_paths)
        x = x + (r - q) * dt + K0 + K1 * v + K2 * v_new + np.sqrt(np.maximum(K3 * v + K4 * v_new, 0.0)) * zs
        v = v_new
        if return_paths:
            xs[i + 1], vs[i + 1] = x, v

    if return_paths:
        return np.exp(x), np.exp(xs), vs
    return np.exp(x)
