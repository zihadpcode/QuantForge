"""Portfolio construction.

* Mean-variance: global minimum variance, tangency (max Sharpe) and the
  efficient frontier, both unconstrained (closed form) and long-only (SLSQP).
* Risk parity / risk budgeting via the strictly convex formulation of
  Spinu (2013): ``min_y 1/2 y'Sy - sum b_i ln y_i``, whose unique solution,
  normalised, equalises risk contributions to the budget ``b``.
* Ledoit-Wolf (2004) shrinkage of the sample covariance towards a scaled
  identity, with the analytically optimal shrinkage intensity.
"""

from __future__ import annotations

import numpy as np
from scipy import optimize

__all__ = [
    "min_variance",
    "tangency",
    "efficient_frontier",
    "risk_contributions",
    "risk_parity",
    "ledoit_wolf",
]


def _solve_long_only(obj, grad, n, extra_cons=()):
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones(n)}, *extra_cons]
    sol = optimize.minimize(obj, np.full(n, 1.0 / n), jac=grad, method="SLSQP", bounds=[(0.0, 1.0)] * n,
                            constraints=cons, options={"ftol": 1e-14, "maxiter": 1000})
    if not sol.success:
        raise RuntimeError(sol.message)
    w = np.clip(sol.x, 0.0, None)
    return w / w.sum()


def min_variance(cov, long_only: bool = False) -> np.ndarray:
    cov = np.asarray(cov, float)
    n = cov.shape[0]
    if not long_only:
        x = np.linalg.solve(cov, np.ones(n))
        return x / x.sum()
    return _solve_long_only(lambda w: w @ cov @ w, lambda w: 2 * cov @ w, n)


def tangency(mu, cov, rf: float = 0.0, long_only: bool = False) -> np.ndarray:
    """Maximum Sharpe ratio portfolio (assumes some asset beats rf)."""
    mu, cov = np.asarray(mu, float), np.asarray(cov, float)
    ex = mu - rf
    if not long_only:
        x = np.linalg.solve(cov, ex)
        return x / x.sum()

    def neg_sharpe(w):
        return -(w @ ex) / np.sqrt(w @ cov @ w)

    def grad(w):
        s = np.sqrt(w @ cov @ w)
        return -(ex * s - (w @ ex) * (cov @ w) / s) / (s * s)

    return _solve_long_only(neg_sharpe, grad, mu.size)


def efficient_frontier(mu, cov, n_points: int = 50, long_only: bool = False):
    """Return (target_returns, vols, weights) along the efficient frontier."""
    mu, cov = np.asarray(mu, float), np.asarray(cov, float)
    n = mu.size
    w_mv = min_variance(cov, long_only)
    r_lo = w_mv @ mu
    r_hi = mu.max() if long_only else r_lo + 2.0 * (mu.max() - r_lo)
    targets = np.linspace(r_lo, r_hi, n_points)
    W = []
    if not long_only:
        # two-fund theorem: closed-form Lagrangian solution
        inv = np.linalg.inv(cov)
        one = np.ones(n)
        A, B, C = one @ inv @ one, one @ inv @ mu, mu @ inv @ mu
        D = A * C - B * B
        for m in targets:
            lam, gam = (C - m * B) / D, (m * A - B) / D
            W.append(inv @ (lam * one + gam * mu))
    else:
        for m in targets:
            cons = ({"type": "eq", "fun": lambda w, m=m: w @ mu - m, "jac": lambda w: mu},)
            W.append(_solve_long_only(lambda w: w @ cov @ w, lambda w: 2 * cov @ w, n, cons))
    W = np.array(W)
    vols = np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W))
    return targets, vols, W


def risk_contributions(w, cov) -> np.ndarray:
    """Fractional contribution of each asset to portfolio variance (sums to 1)."""
    w, cov = np.asarray(w, float), np.asarray(cov, float)
    return w * (cov @ w) / (w @ cov @ w)


def risk_parity(cov, budget=None, tol: float = 1e-12) -> np.ndarray:
    """Long-only risk-budgeting portfolio (equal risk contribution by default).

    Solved by Newton's method on the convex Spinu objective with backtracking
    line search keeping ``y > 0``.
    """
    cov = np.asarray(cov, float)
    n = cov.shape[0]
    b = np.full(n, 1.0 / n) if budget is None else np.asarray(budget, float) / np.sum(budget)
    y = b / np.sqrt(np.diag(cov))  # inverse-vol style start

    def f(y):
        return 0.5 * y @ cov @ y - b @ np.log(y)

    for _ in range(100):
        g = cov @ y - b / y
        if np.max(np.abs(g)) < tol:
            break
        H = cov + np.diag(b / y**2)
        step = np.linalg.solve(H, g)
        t = 1.0
        while np.any(y - t * step <= 0) or f(y - t * step) > f(y) - 1e-4 * t * (g @ step):
            t *= 0.5
            if t < 1e-12:
                break
        y = y - t * step
    return y / y.sum()


def ledoit_wolf(X, assume_centered: bool = False):
    """Ledoit-Wolf shrinkage covariance. Returns (shrunk_cov, shrinkage)."""
    X = np.asarray(X, float)
    if not assume_centered:
        X = X - X.mean(axis=0)
    n, p = X.shape
    S = X.T @ X / n
    mu = np.trace(S) / p
    delta = np.sum((S - mu * np.eye(p)) ** 2) / p
    X2 = X * X
    beta = (np.sum(X2.T @ X2) / n - np.sum(S * S)) / (n * p)
    shrink = 0.0 if delta == 0 else min(beta, delta) / delta
    return (1.0 - shrink) * S + shrink * mu * np.eye(p), float(shrink)
