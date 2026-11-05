"""Interest-rate tools: curve construction and short-rate models.

* Bootstrapping discount factors from par swap/bond yields.
* Nelson-Siegel-Svensson zero curve fitting.
* Vasicek and CIR affine short-rate models: closed-form zero-coupon bonds,
  Jamshidian's zero-coupon bond option formula (Vasicek), and exact transition
  sampling for Monte Carlo (Gaussian for Vasicek, non-central chi-square for
  CIR).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize

from .blackscholes import norm_cdf as N

__all__ = [
    "bootstrap_par_curve",
    "par_rates_from_discount",
    "nss_yield",
    "fit_nss",
    "Vasicek",
    "CIR",
]


# ---------------------------------------------------------------------------
# Curve construction
# ---------------------------------------------------------------------------
def bootstrap_par_curve(maturities, par_rates, freq: int = 1) -> np.ndarray:
    """Discount factors from par yields of bullet bonds/swaps.

    ``maturities`` must be the full coupon grid ``1/freq, 2/freq, ..., n/freq``.
    For a par instrument with coupon ``c`` paid ``freq`` times a year::

        1 = (c/freq) * sum_{i<=n} D_i + D_n  =>  D_n = (1 - (c/freq) sum_{i<n} D_i) / (1 + c/freq)
    """
    t = np.asarray(maturities, float)
    c = np.asarray(par_rates, float) / freq
    expected = np.arange(1, t.size + 1) / freq
    if not np.allclose(t, expected):
        raise ValueError("maturities must be the consecutive coupon grid 1/freq, 2/freq, ...")
    D = np.empty_like(c)
    annuity = 0.0
    for i in range(c.size):
        D[i] = (1.0 - c[i] * annuity) / (1.0 + c[i])
        annuity += D[i]
    return D


def par_rates_from_discount(D, freq: int = 1) -> np.ndarray:
    """Inverse of :func:`bootstrap_par_curve`."""
    D = np.asarray(D, float)
    return freq * (1.0 - D) / np.cumsum(D)


def nss_yield(t, beta0, beta1, beta2, beta3, tau1, tau2):
    """Nelson-Siegel-Svensson continuously compounded zero yield."""
    t = np.maximum(np.asarray(t, float), 1e-10)
    x1, x2 = t / tau1, t / tau2
    f1 = (1 - np.exp(-x1)) / x1
    f2 = f1 - np.exp(-x1)
    f3 = (1 - np.exp(-x2)) / x2 - np.exp(-x2)
    return beta0 + beta1 * f1 + beta2 * f2 + beta3 * f3


def fit_nss(t, y):
    """Least-squares NSS fit; grid of (tau1, tau2) starts. Returns (params, rmse)."""
    t, y = np.asarray(t, float), np.asarray(y, float)

    def resid(p):
        return nss_yield(t, *p) - y

    lb = [-1.0, -1.0, -1.0, -1.0, 0.05, 0.05]
    ub = [1.0, 1.0, 1.0, 1.0, 30.0, 30.0]
    best = None
    for tau1 in (0.5, 2.0, 5.0):
        for tau2 in (1.0, 8.0, 15.0):
            x0 = [y[-1], y[0] - y[-1], 0.0, 0.0, tau1, tau2]
            sol = optimize.least_squares(resid, x0, bounds=(lb, ub), xtol=1e-14, ftol=1e-14)
            if best is None or sol.cost < best.cost:
                best = sol
    return best.x, float(np.sqrt(np.mean(best.fun**2)))


# ---------------------------------------------------------------------------
# Short-rate models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Vasicek:
    """dr = a (b - r) dt + sigma dW."""

    a: float
    b: float
    sigma: float

    def _B(self, tau):
        return (1.0 - np.exp(-self.a * tau)) / self.a

    def zcb(self, r, tau):
        """Zero-coupon bond price P(t, t + tau) given short rate r."""
        a, b, s = self.a, self.b, self.sigma
        B = self._B(tau)
        lnA = (B - tau) * (a * a * b - 0.5 * s * s) / (a * a) - s * s * B * B / (4.0 * a)
        return np.exp(lnA - B * r)

    def zero_yield(self, r, tau):
        return -np.log(self.zcb(r, tau)) / tau

    def zcb_option(self, r0, T, S, X, is_call=True):
        """Option expiring at T on the zero-coupon bond maturing at S > T (Jamshidian 1989)."""
        a, s = self.a, self.sigma
        PT, PS = self.zcb(r0, T), self.zcb(r0, S)
        sp = s / a * (1.0 - np.exp(-a * (S - T))) * np.sqrt((1.0 - np.exp(-2.0 * a * T)) / (2.0 * a))
        h = np.log(PS / (X * PT)) / sp + 0.5 * sp
        if is_call:
            return PS * N(h) - X * PT * N(h - sp)
        return X * PT * N(-h + sp) - PS * N(-h)

    def simulate(self, r0, T, n_steps, n_paths, seed=None):
        """Exact simulation; returns array (n_paths, n_steps + 1)."""
        rng = np.random.default_rng(seed)
        dt = T / n_steps
        e = np.exp(-self.a * dt)
        sd = self.sigma * np.sqrt((1.0 - e * e) / (2.0 * self.a))
        r = np.empty((n_paths, n_steps + 1))
        r[:, 0] = r0
        for i in range(n_steps):
            r[:, i + 1] = r[:, i] * e + self.b * (1.0 - e) + sd * rng.standard_normal(n_paths)
        return r


@dataclass(frozen=True)
class CIR:
    """dr = a (b - r) dt + sigma sqrt(r) dW."""

    a: float
    b: float
    sigma: float

    @property
    def feller(self) -> bool:
        return 2.0 * self.a * self.b >= self.sigma**2

    def zcb(self, r, tau):
        a, b, s = self.a, self.b, self.sigma
        g = np.sqrt(a * a + 2.0 * s * s)
        eg = np.exp(g * tau) - 1.0
        den = (g + a) * eg + 2.0 * g
        B = 2.0 * eg / den
        A = (2.0 * g * np.exp(0.5 * (a + g) * tau) / den) ** (2.0 * a * b / s**2)
        return A * np.exp(-B * r)

    def zero_yield(self, r, tau):
        return -np.log(self.zcb(r, tau)) / tau

    def simulate(self, r0, T, n_steps, n_paths, seed=None):
        """Exact simulation via the scaled non-central chi-square transition law."""
        rng = np.random.default_rng(seed)
        dt = T / n_steps
        e = np.exp(-self.a * dt)
        c = self.sigma**2 * (1.0 - e) / (4.0 * self.a)
        df = 4.0 * self.a * self.b / self.sigma**2
        r = np.empty((n_paths, n_steps + 1))
        r[:, 0] = r0
        for i in range(n_steps):
            r[:, i + 1] = c * rng.noncentral_chisquare(df, r[:, i] * e / c)
        return r
