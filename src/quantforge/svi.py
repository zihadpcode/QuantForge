"""SVI / SSVI implied volatility parameterisations and static-arbitrage checks.

Notation (Gatheral): log-moneyness ``k = ln(K / F_T)``, total implied variance
``w(k, T) = sigma_BS(k, T)^2 * T``.

Raw SVI (Gatheral 2004)::

    w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + s^2))

SSVI (Gatheral & Jacquier 2014)::

    w(k, theta) = theta / 2 * (1 + rho*phi*k + sqrt((phi*k + rho)^2 + 1 - rho^2))
    phi(theta)  = eta / (theta^gamma * (1 + theta)^(1 - gamma))     (power law)

Static arbitrage
----------------
* Butterfly: the risk-neutral density is non-negative iff
  ``g(k) = (1 - k w'/(2w))^2 - w'^2/4 (1/w + 1/4) + w''/2 >= 0``.
* Calendar: total variance is non-decreasing in T at every fixed k.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from scipy import optimize

__all__ = [
    "RawSVI",
    "fit_raw_svi",
    "SVIFit",
    "durrleman_g",
    "butterfly_arbitrage",
    "calendar_arbitrage",
    "SSVI",
    "SVISurface",
]


# ---------------------------------------------------------------------------
# Raw SVI
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RawSVI:
    a: float
    b: float
    rho: float
    m: float
    s: float

    def w(self, k):
        k = np.asarray(k, dtype=float)
        x = k - self.m
        return self.a + self.b * (self.rho * x + np.sqrt(x * x + self.s**2))

    def dw(self, k):
        x = np.asarray(k, dtype=float) - self.m
        return self.b * (self.rho + x / np.sqrt(x * x + self.s**2))

    def d2w(self, k):
        x = np.asarray(k, dtype=float) - self.m
        return self.b * self.s**2 / (x * x + self.s**2) ** 1.5

    def implied_vol(self, k, T):
        return np.sqrt(np.maximum(self.w(k), 0.0) / T)

    @property
    def min_variance(self) -> float:
        return self.a + self.b * self.s * np.sqrt(1.0 - self.rho**2)

    @property
    def lee_ok(self) -> bool:
        """Roger Lee's moment bound on the wing slopes: b (1 + |rho|) <= 2."""
        return self.b * (1.0 + abs(self.rho)) <= 2.0 + 1e-12

    def g(self, k):
        return durrleman_g(self.w(k), self.dw(k), self.d2w(k), k)


def durrleman_g(w, dw, d2w, k):
    """Durrleman's butterfly condition function (density = g * normal pdf / sqrt(w))."""
    w, dw, d2w, k = map(np.asarray, (w, dw, d2w, k))
    return (1.0 - k * dw / (2.0 * w)) ** 2 - dw**2 / 4.0 * (1.0 / w + 0.25) + d2w / 2.0


@dataclass
class SVIFit:
    params: RawSVI
    rmse_w: float  # RMSE in total variance
    rmse_iv: float  # RMSE in implied vol
    butterfly_free: bool


def _raw_from_x(x) -> RawSVI:
    vmin, b, rho, m, s = x
    return RawSVI(a=vmin - b * s * np.sqrt(1.0 - rho**2), b=b, rho=rho, m=m, s=s)


def fit_raw_svi(
    k,
    iv,
    T: float,
    weights=None,
    enforce_lee: bool = True,
) -> SVIFit:
    """Fit raw SVI to one smile.

    The fit is parameterised by ``(w_min, b, rho, m, s)`` with ``w_min >= 0``,
    which builds the requirement of non-negative total variance into simple box
    bounds (``a = w_min - b s sqrt(1 - rho^2)``). A small grid of starting points
    for ``(m, s)`` makes the non-convex fit robust. Residuals are in implied
    vol, so the objective is directly interpretable.
    """
    k = np.asarray(k, dtype=float)
    iv = np.asarray(iv, dtype=float)
    w_mkt = iv**2 * T
    wts = np.ones_like(k) if weights is None else np.asarray(weights, dtype=float)
    wts = np.sqrt(wts / wts.mean())

    span = max(k.max() - k.min(), 0.1)
    lb = np.array([0.0, 0.0, -0.999, k.min() - span, 1e-4])
    ub = np.array([w_mkt.max() * 2.0 + 1e-6, 5.0, 0.999, k.max() + span, 5.0 * span])

    def resid(x):
        p = _raw_from_x(x)
        model_iv = np.sqrt(np.maximum(p.w(k), 1e-14) / T)
        r = (model_iv - iv) * wts
        if enforce_lee:
            excess = max(p.b * (1.0 + abs(p.rho)) - 2.0, 0.0)
            r = np.append(r, 10.0 * excess)
        return r

    best = None
    vmin0 = max(w_mkt.min() * 0.9, 1e-6)
    k_atm = k[np.argmin(w_mkt)]
    for m0 in (k_atm, 0.0, k_atm - 0.1 * span, k_atm + 0.1 * span):
        for s0 in (0.05 * span, 0.2 * span, 0.5 * span):
            for rho0 in (-0.5, 0.0):
                x0 = np.clip([vmin0, 0.1, rho0, m0, s0], lb + 1e-8, ub - 1e-8)
                sol = optimize.least_squares(
                    resid, x0, bounds=(lb, ub), method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=5000
                )
                if best is None or sol.cost < best.cost:
                    best = sol

    p = _raw_from_x(best.x)
    w_fit = p.w(k)
    kk = np.linspace(k.min() - 1.0, k.max() + 1.0, 2001)
    return SVIFit(
        params=p,
        rmse_w=float(np.sqrt(np.mean((w_fit - w_mkt) ** 2))),
        rmse_iv=float(np.sqrt(np.mean((np.sqrt(np.maximum(w_fit, 0) / T) - iv) ** 2))),
        butterfly_free=bool(np.all(p.g(kk) >= -1e-10) and p.min_variance >= 0),
    )


def butterfly_arbitrage(w_fn: Callable, k_grid, h: float = 1e-4):
    """Evaluate Durrleman's ``g`` on a grid for any total-variance function of k.

    Returns ``(g_values, is_free)``. Derivatives are central finite differences.
    """
    k = np.asarray(k_grid, dtype=float)
    w0, wp, wm = w_fn(k), w_fn(k + h), w_fn(k - h)
    dw = (wp - wm) / (2 * h)
    d2w = (wp - 2 * w0 + wm) / (h * h)
    g = durrleman_g(w0, dw, d2w, k)
    return g, bool(np.all(g >= -1e-8) and np.all(w0 > 0))


def calendar_arbitrage(w_slices: Sequence[Callable], k_grid, tol: float = 1e-12):
    """Check total variance is non-decreasing across ordered maturity slices.

    Returns ``(worst_violation, is_free)`` where ``worst_violation`` is the most
    negative ``w_{i+1}(k) - w_i(k)`` found (0 if none).
    """
    k = np.asarray(k_grid, dtype=float)
    ws = np.array([f(k) for f in w_slices])
    diffs = np.diff(ws, axis=0)
    worst = float(min(diffs.min(), 0.0)) if diffs.size else 0.0
    return worst, worst >= -tol


# ---------------------------------------------------------------------------
# SSVI surface
# ---------------------------------------------------------------------------
class SSVI:
    """Surface SVI with power-law ``phi``.

    Parameters
    ----------
    theta_fn : callable
        ATM total variance curve ``theta(T)``; must be increasing with
        ``theta(0) = 0``.
    rho, eta, gamma : float
        Skew correlation and power-law parameters. Gatheral & Jacquier show the
        surface is free of static arbitrage when ``eta (1 + |rho|) <= 2`` and
        ``0 < gamma <= 1/2``.
    """

    def __init__(self, theta_fn: Callable, rho: float, eta: float, gamma: float):
        self.theta_fn = theta_fn
        self.rho, self.eta, self.gamma = rho, eta, gamma

    @classmethod
    def heston_like(cls, v0, v_inf, kappa, rho, eta, gamma):
        """ATM variance curve equal to Heston's expected integrated variance."""

        def theta(T):
            T = np.asarray(T, dtype=float)
            return v_inf * T + (v0 - v_inf) * (1.0 - np.exp(-kappa * T)) / kappa

        return cls(theta, rho, eta, gamma)

    def phi(self, theta):
        return self.eta / (theta**self.gamma * (1.0 + theta) ** (1.0 - self.gamma))

    @property
    def gatheral_jacquier_sufficient(self) -> bool:
        return self.eta * (1.0 + abs(self.rho)) <= 2.0 and 0.0 < self.gamma <= 0.5

    def total_variance(self, k, T):
        k, T = np.broadcast_arrays(np.asarray(k, float), np.asarray(T, float))
        th = self.theta_fn(T)
        p = self.phi(th)
        r = self.rho
        return 0.5 * th * (1.0 + r * p * k + np.sqrt((p * k + r) ** 2 + 1.0 - r * r))

    def implied_vol(self, k, T):
        return np.sqrt(self.total_variance(k, T) / np.asarray(T, float))


# ---------------------------------------------------------------------------
# Surface from raw SVI slices
# ---------------------------------------------------------------------------
class SVISurface:
    """Implied-vol surface built from per-expiry raw SVI slices.

    Between expiries total variance is interpolated linearly in ``T`` at fixed
    log-moneyness, which preserves the absence of calendar arbitrage whenever
    the slices themselves do not cross. Before the first expiry ``w`` is scaled
    linearly to 0 at ``T = 0``; beyond the last, implied vol is held flat.
    """

    def __init__(self, expiries: Sequence[float], slices: Sequence[RawSVI]):
        order = np.argsort(expiries)
        self.T = np.asarray(expiries, float)[order]
        self.slices = [slices[i] for i in order]

    def total_variance(self, k, T):
        k, T = np.broadcast_arrays(np.asarray(k, float), np.asarray(T, float))
        out = np.empty(k.shape)
        Ts = self.T
        flat_k, flat_T, flat_out = k.ravel(), T.ravel(), out.reshape(-1)
        idx = np.searchsorted(Ts, flat_T, side="left")  # first slice with Ts >= T
        for j in np.unique(idx):
            m = idx == j
            kk, tt = flat_k[m], flat_T[m]
            if j == 0:
                flat_out[m] = self.slices[0].w(kk) * tt / Ts[0]
            elif j >= len(Ts):
                flat_out[m] = self.slices[-1].w(kk) * tt / Ts[-1]
            else:
                t0, t1 = Ts[j - 1], Ts[j]
                a = (tt - t0) / (t1 - t0)
                flat_out[m] = (1 - a) * self.slices[j - 1].w(kk) + a * self.slices[j].w(kk)
        return out

    def implied_vol(self, k, T):
        return np.sqrt(np.maximum(self.total_variance(k, T), 0.0) / np.asarray(T, float))

    def arbitrage_report(self, k_grid=None) -> dict:
        k_grid = np.linspace(-1.5, 1.5, 601) if k_grid is None else k_grid
        fly = [bool(np.all(s.g(k_grid) >= -1e-10)) for s in self.slices]
        worst, cal_ok = calendar_arbitrage([s.w for s in self.slices], k_grid)
        return {"butterfly_free_by_slice": fly, "calendar_worst": worst, "calendar_free": cal_ok}
