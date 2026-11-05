"""GARCH(1,1) volatility model with Gaussian quasi-maximum likelihood.

    r_t = mu + eps_t,  eps_t = sigma_t z_t,
    sigma_t^2 = omega + alpha eps_{t-1}^2 + beta sigma_{t-1}^2

The variance recursion is a first-order IIR filter, so the log-likelihood is
evaluated with ``scipy.signal.lfilter`` (no Python loop). Returns are
standardised internally for numerical conditioning and parameters mapped back.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize, signal

__all__ = ["GarchParams", "GarchFit", "fit_garch", "garch_variance", "simulate_garch"]


@dataclass(frozen=True)
class GarchParams:
    mu: float
    omega: float
    alpha: float
    beta: float

    @property
    def persistence(self) -> float:
        return self.alpha + self.beta

    @property
    def long_run_variance(self) -> float:
        return self.omega / (1.0 - self.persistence)

    @property
    def half_life(self) -> float:
        """Days for a variance shock to decay by half."""
        return float(np.log(0.5) / np.log(self.persistence))


@dataclass
class GarchFit:
    params: GarchParams
    stderr: dict
    loglik: float
    conditional_var: np.ndarray  # sigma_t^2 for t = 1..n
    next_var: float  # sigma_{n+1}^2

    def forecast(self, horizon: int) -> np.ndarray:
        """h-step ahead conditional variances sigma^2_{n+1..n+h}."""
        p = self.params
        h = np.arange(horizon)
        return p.long_run_variance + p.persistence**h * (self.next_var - p.long_run_variance)


def garch_variance(eps, omega, alpha, beta, sigma2_0):
    """Return (sigma^2_1..sigma^2_n, sigma^2_{n+1}) for innovations eps_1..eps_n.

    ``sigma2_0`` is the variance used for the first observation.
    """
    eps2 = np.asarray(eps, float) ** 2
    # s_t = omega + alpha*eps2_{t-1} + beta*s_{t-1}, t = 2..n+1, with s_1 = sigma2_0
    x = omega + alpha * eps2
    tail, _ = signal.lfilter([1.0], [1.0, -beta], x, zi=[beta * sigma2_0])
    s = np.concatenate([[sigma2_0], tail])
    return s[:-1], float(s[-1])


def _nll(theta, r):
    mu, omega, alpha, beta = theta
    eps = r - mu
    s2, _ = garch_variance(eps, omega, alpha, beta, eps.var())
    s2 = np.maximum(s2, 1e-300)
    return 0.5 * np.sum(np.log(2 * np.pi) + np.log(s2) + eps * eps / s2)


def _num_hessian(f, x, h=1e-4):
    n = x.size
    H = np.empty((n, n))
    for i in range(n):
        for j in range(i, n):
            ei, ej = np.zeros(n), np.zeros(n)
            ei[i] = h * max(abs(x[i]), 1e-2)
            ej[j] = h * max(abs(x[j]), 1e-2)
            H[i, j] = H[j, i] = (
                f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej) + f(x - ei - ej)
            ) / (4 * ei[i] * ej[j])
    return H


def fit_garch(returns) -> GarchFit:
    """Fit GARCH(1,1) by Gaussian (Q)MLE with stationarity constraint alpha+beta<1."""
    r_raw = np.asarray(returns, float)
    scale = r_raw.std()
    r = r_raw / scale

    best = None
    cons = ({"type": "ineq", "fun": lambda th: 0.99999 - th[2] - th[3]},)
    bounds = [(-1.0, 1.0), (1e-8, 10.0), (0.0, 1.0), (0.0, 1.0)]
    for a0, b0 in ((0.05, 0.90), (0.10, 0.80), (0.02, 0.97)):
        x0 = np.array([r.mean(), (1 - a0 - b0), a0, b0])
        sol = optimize.minimize(_nll, x0, args=(r,), method="SLSQP", bounds=bounds, constraints=cons,
                                options={"ftol": 1e-12, "maxiter": 1000})
        if best is None or sol.fun < best.fun:
            best = sol
    th = best.x

    # standard errors from the inverse Hessian of the scaled problem
    try:
        cov = np.linalg.inv(_num_hessian(lambda t: _nll(t, r), th))
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        se = np.full(4, np.nan)

    mu, omega, alpha, beta = th
    params = GarchParams(mu=mu * scale, omega=omega * scale**2, alpha=alpha, beta=beta)
    eps = r_raw - params.mu
    s2, nxt = garch_variance(eps, params.omega, alpha, beta, eps.var())
    loglik = -_nll(th, r) - r.size * np.log(scale)  # Jacobian of the rescaling
    return GarchFit(
        params=params,
        stderr={"mu": se[0] * scale, "omega": se[1] * scale**2, "alpha": se[2], "beta": se[3]},
        loglik=float(loglik),
        conditional_var=s2,
        next_var=nxt,
    )


def simulate_garch(params: GarchParams, n: int, seed=None, burn: int = 1000, dist: str = "normal", nu: float = 6.0):
    """Simulate returns and conditional variances (unit-variance Gaussian or Student-t shocks)."""
    rng = np.random.default_rng(seed)
    total = n + burn
    if dist == "normal":
        z = rng.standard_normal(total)
    elif dist == "t":
        z = rng.standard_t(nu, total) * np.sqrt((nu - 2.0) / nu)
    else:
        raise ValueError("dist must be 'normal' or 't'")
    s2 = np.empty(total)
    eps = np.empty(total)
    s2[0] = params.long_run_variance
    for t in range(total):
        if t > 0:
            s2[t] = params.omega + params.alpha * eps[t - 1] ** 2 + params.beta * s2[t - 1]
        eps[t] = np.sqrt(s2[t]) * z[t]
    return params.mu + eps[burn:], s2[burn:]
