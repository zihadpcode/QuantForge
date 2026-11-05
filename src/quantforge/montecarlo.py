"""Monte Carlo engine for Black-Scholes dynamics with variance reduction.

* exact GBM path simulation, pseudo-random or scrambled Sobol (QMC);
* antithetic variates and control variates (with the optimal, regression
  estimated coefficient);
* arithmetic Asian options with the geometric Asian as control variate;
* barrier options with a Brownian-bridge crossing correction, which removes
  the O(sqrt(dt)) discrete-monitoring bias;
* American options by Longstaff-Schwartz least-squares Monte Carlo, with an
  optional out-of-sample policy evaluation that yields a true lower bound.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtri
from scipy.stats import qmc

from . import blackscholes as bs
from .exotics import geometric_asian

__all__ = [
    "MCResult",
    "normals",
    "gbm_paths",
    "european_mc",
    "asian_mc",
    "barrier_mc",
    "longstaff_schwartz",
]


@dataclass
class MCResult:
    price: float
    stderr: float
    n_paths: int
    variance_reduction: float | None = None  # var(plain) / var(estimator)

    @property
    def ci95(self) -> tuple[float, float]:
        return self.price - 1.96 * self.stderr, self.price + 1.96 * self.stderr


def normals(n_paths: int, dim: int, rng: np.random.Generator, method: str = "pseudo") -> np.ndarray:
    """Standard normal draws of shape ``(n_paths, dim)``.

    ``method='sobol'`` uses Owen-scrambled Sobol points mapped through the
    inverse normal CDF; ``n_paths`` should be a power of two.
    """
    if method == "pseudo":
        return rng.standard_normal((n_paths, dim))
    if method == "sobol":
        sob = qmc.Sobol(d=dim, scramble=True, seed=rng)
        u = sob.random(n_paths)
        return ndtri(np.clip(u, 1e-16, 1 - 1e-16))
    raise ValueError("method must be 'pseudo' or 'sobol'")


def gbm_paths(
    S0, T, r, sigma, q=0.0, n_steps=252, n_paths=100_000, seed=None, antithetic=False, method="pseudo"
) -> np.ndarray:
    """Exact GBM paths, shape ``(n_paths, n_steps + 1)`` including ``S0``."""
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    m = n_paths // 2 if antithetic else n_paths
    z = normals(m, n_steps, rng, method)
    if antithetic:
        z = np.vstack([z, -z])
    incr = (r - q - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    logS = np.log(S0) + np.concatenate([np.zeros((z.shape[0], 1)), np.cumsum(incr, axis=1)], axis=1)
    return np.exp(logS)


def _cv_adjust(y: np.ndarray, x: np.ndarray, x_mean: float):
    """Control-variate estimator with the optimal coefficient b* = cov(y,x)/var(x)."""
    c = np.cov(y, x)
    beta = c[0, 1] / c[1, 1]
    return y - beta * (x - x_mean)


def _pairwise_mean(v: np.ndarray, antithetic: bool) -> np.ndarray:
    """Average antithetic pairs so the standard error accounts for their correlation."""
    if not antithetic:
        return v
    h = v.size // 2
    return 0.5 * (v[:h] + v[h:])


def european_mc(
    S0, K, T, r, sigma, q=0.0, is_call=True, n_paths=100_000, seed=None,
    antithetic=False, control_variate=False, method="pseudo", qmc_reps=16,
) -> MCResult:
    """European vanilla by Monte Carlo (single step, exact terminal law).

    Control variate: the discounted terminal stock, whose expectation
    ``S0 e^{-qT}`` is known exactly.

    With ``method='sobol'`` the paths are split into ``qmc_reps`` independently
    scrambled Sobol sequences (randomised QMC). QMC points are not independent,
    so the standard error is taken from the dispersion of the replicate means,
    which is the only statistically valid error estimate for QMC.
    """
    rng = np.random.default_rng(seed)
    w = 1.0 if is_call else -1.0
    disc = np.exp(-r * T)

    def estimates(n):
        m = n // 2 if antithetic else n
        z = normals(m, 1, rng, method)[:, 0]
        if antithetic:
            z = np.concatenate([z, -z])
        ST = S0 * np.exp((r - q - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z)
        pay = disc * np.maximum(w * (ST - K), 0.0)
        est = _cv_adjust(pay, disc * ST, S0 * np.exp(-q * T)) if control_variate else pay
        return pay, est

    if method == "sobol":
        n_rep = max(n_paths // qmc_reps, 2)
        means = np.array([estimates(n_rep)[1].mean() for _ in range(qmc_reps)])
        return MCResult(
            price=float(means.mean()),
            stderr=float(means.std(ddof=1) / np.sqrt(qmc_reps)),
            n_paths=n_rep * qmc_reps,
        )

    pay, est = estimates(n_paths)
    samples = _pairwise_mean(est, antithetic)
    var_of_mean = samples.var(ddof=1) / samples.size
    plain_var_of_mean = pay.var(ddof=1) / pay.size
    return MCResult(
        price=float(samples.mean()),
        stderr=float(np.sqrt(var_of_mean)),
        n_paths=int(est.size),
        variance_reduction=float(plain_var_of_mean / var_of_mean) if var_of_mean > 0 else np.inf,
    )


def asian_mc(
    S0, K, T, r, sigma, q=0.0, n_fix=52, is_call=True, n_paths=100_000, seed=None,
    control_variate=True, antithetic=False,
) -> MCResult:
    """Arithmetic-average Asian option; geometric Asian as control variate."""
    S = gbm_paths(S0, T, r, sigma, q, n_fix, n_paths, seed, antithetic)[:, 1:]
    w = 1.0 if is_call else -1.0
    disc = np.exp(-r * T)
    arith = disc * np.maximum(w * (S.mean(axis=1) - K), 0.0)
    plain_var = arith.var(ddof=1)
    est = arith
    if control_variate:
        geo = disc * np.maximum(w * (np.exp(np.log(S).mean(axis=1)) - K), 0.0)
        est = _cv_adjust(arith, geo, geometric_asian(S0, K, T, r, sigma, q, n_fix, is_call))
    samples = _pairwise_mean(est, antithetic)
    var_of_mean = samples.var(ddof=1) / samples.size
    return MCResult(
        price=float(samples.mean()),
        stderr=float(np.sqrt(var_of_mean)),
        n_paths=int(est.size),
        variance_reduction=float((plain_var / arith.size) / var_of_mean),
    )


def barrier_mc(
    S0, K, H, T, r, sigma, q=0.0, n_steps=252, n_paths=100_000, seed=None, brownian_bridge=True,
) -> MCResult:
    """Down-and-out call with continuous monitoring.

    With ``brownian_bridge=True`` each path is weighted by the probability that
    the Brownian bridge between consecutive grid points did not touch the
    barrier: ``prod_i [1 - exp(-2 (x_i - h)(x_{i+1} - h) / (sigma^2 dt))]``.
    This is a conditional-expectation estimator: unbiased for the
    continuously monitored product and lower variance than counting crossings.
    """
    S = gbm_paths(S0, T, r, sigma, q, n_steps, n_paths, seed)
    x = np.log(S) - np.log(H)
    dt = T / n_steps
    alive = np.all(x > 0, axis=1).astype(float)
    if brownian_bridge:
        with np.errstate(over="ignore"):
            p_hit = np.exp(-2.0 * x[:, :-1] * x[:, 1:] / (sigma**2 * dt))
        survive = np.prod(np.clip(1.0 - p_hit, 0.0, 1.0), axis=1) * alive
    else:
        survive = alive
    pay = np.exp(-r * T) * np.maximum(S[:, -1] - K, 0.0) * survive
    return MCResult(price=float(pay.mean()), stderr=float(pay.std(ddof=1) / np.sqrt(n_paths)), n_paths=n_paths)


def _basis(x: np.ndarray, degree: int) -> np.ndarray:
    """Weighted Laguerre polynomials exp(-x/2) L_n(x), as in Longstaff-Schwartz."""
    cols = [np.ones_like(x)]
    ex = np.exp(-0.5 * x)
    L_prev, L = np.ones_like(x), 1.0 - x
    for n in range(1, degree + 1):
        cols.append(ex * L)
        L_prev, L = L, ((2 * n + 1 - x) * L - n * L_prev) / (n + 1)
    return np.column_stack(cols)


def longstaff_schwartz(
    S0, K, T, r, sigma, q=0.0, is_call=False, n_exercise=50, n_paths=100_000, degree=3,
    seed=None, out_of_sample=True,
) -> MCResult:
    """American option by least-squares Monte Carlo (Longstaff & Schwartz 2001).

    Regression of discounted continuation values on weighted Laguerre
    polynomials of ``S/K`` over in-the-money paths only. With
    ``out_of_sample=True`` the exercise boundary is estimated on one set of
    paths and applied to an independent set, so the reported price is an
    unbiased estimate of a *feasible* exercise policy, i.e. a lower bound on the
    true American price (free of the in-sample foresight bias).
    """
    dt = T / n_exercise
    disc = np.exp(-r * dt)
    w = 1.0 if is_call else -1.0
    rng = np.random.default_rng(seed)
    seeds = rng.integers(0, 2**63 - 1, size=2)

    def simulate(s):
        return gbm_paths(S0, T, r, sigma, q, n_exercise, n_paths, int(s), antithetic=True)

    # --- backward induction on training paths: estimate regression coefs ---
    S = simulate(seeds[0])
    cash = np.maximum(w * (S[:, -1] - K), 0.0)
    coefs: dict[int, np.ndarray] = {}
    for t in range(n_exercise - 1, 0, -1):
        cash *= disc
        St = S[:, t]
        exercise = np.maximum(w * (St - K), 0.0)
        itm = exercise > 0
        if itm.sum() <= degree + 1:
            continue
        X = _basis(St[itm] / K, degree)
        beta, *_ = np.linalg.lstsq(X, cash[itm], rcond=None)
        coefs[t] = beta
        cont = X @ beta
        ex_now = exercise[itm] > cont
        idx = np.flatnonzero(itm)[ex_now]
        cash[idx] = exercise[idx]
    in_sample = disc * cash

    if out_of_sample:
        S = simulate(seeds[1])
        n = S.shape[0]
        value = np.zeros(n)
        alive = np.ones(n, dtype=bool)
        for t in range(1, n_exercise):
            St = S[:, t]
            exercise = np.maximum(w * (St - K), 0.0)
            cand = alive & (exercise > 0)
            if t in coefs and cand.any():
                cont = _basis(St[cand] / K, degree) @ coefs[t]
                stop = np.flatnonzero(cand)[exercise[cand] > cont]
                value[stop] = exercise[stop] * np.exp(-r * t * dt)
                alive[stop] = False
        value[alive] = np.maximum(w * (S[alive, -1] - K), 0.0) * np.exp(-r * T)
        samples = value
    else:
        samples = in_sample

    pairs = _pairwise_mean(samples, True)
    price = float(pairs.mean())
    stderr = float(pairs.std(ddof=1) / np.sqrt(pairs.size))
    # immediate exercise at t=0 is never optimal for these tests, but honour it
    price = max(price, max(w * (S0 - K), 0.0))
    return MCResult(price=price, stderr=stderr, n_paths=int(samples.size))
