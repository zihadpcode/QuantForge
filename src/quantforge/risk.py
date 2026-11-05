"""Market risk: Value-at-Risk, Expected Shortfall and VaR backtesting.

Sign convention: inputs are *returns* (or P&L); VaR and ES are reported as
positive *losses* at confidence level ``alpha`` (e.g. 0.99).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "historical_var_es",
    "normal_var_es",
    "student_t_var_es",
    "cornish_fisher_var",
    "monte_carlo_var_es",
    "BacktestResult",
    "kupiec_pof",
    "christoffersen",
    "backtest_var",
]


def historical_var_es(returns, alpha: float = 0.99):
    """Empirical VaR (quantile) and ES (mean loss beyond VaR)."""
    r = np.asarray(returns, float)
    q = np.quantile(r, 1.0 - alpha)
    tail = r[r <= q]
    return float(-q), float(-tail.mean())


def normal_var_es(mu: float, sigma: float, alpha: float = 0.99):
    z = stats.norm.ppf(alpha)
    var = -mu + sigma * z
    es = -mu + sigma * stats.norm.pdf(z) / (1.0 - alpha)
    return float(var), float(es)


def student_t_var_es(mu: float, sigma: float, nu: float, alpha: float = 0.99):
    """VaR/ES for a Student-t with ``nu > 2`` d.o.f. *scaled to standard deviation* sigma."""
    if nu <= 2:
        raise ValueError("nu must exceed 2 for a finite variance")
    scale = sigma * np.sqrt((nu - 2.0) / nu)
    t = stats.t.ppf(alpha, nu)
    var = -mu + scale * t
    es = -mu + scale * stats.t.pdf(t, nu) / (1.0 - alpha) * (nu + t * t) / (nu - 1.0)
    return float(var), float(es)


def cornish_fisher_var(returns, alpha: float = 0.99):
    """Modified VaR using the Cornish-Fisher expansion for skew and excess kurtosis."""
    r = np.asarray(returns, float)
    mu, sd = r.mean(), r.std(ddof=1)
    s, k = stats.skew(r), stats.kurtosis(r)  # k is excess kurtosis
    z = stats.norm.ppf(1.0 - alpha)
    z_cf = z + (z * z - 1) * s / 6 + (z**3 - 3 * z) * k / 24 - (2 * z**3 - 5 * z) * s * s / 36
    return float(-(mu + sd * z_cf))


def monte_carlo_var_es(weights, mu, cov, alpha=0.99, n_sims=200_000, nu=None, seed=None):
    """Portfolio VaR/ES by simulation from a multivariate normal or Student-t.

    The Student-t is scaled so that ``cov`` is its covariance matrix.
    """
    rng = np.random.default_rng(seed)
    w, mu, cov = np.asarray(weights, float), np.asarray(mu, float), np.asarray(cov, float)
    L = np.linalg.cholesky(cov)
    z = rng.standard_normal((n_sims, w.size)) @ L.T
    if nu is not None:
        g = rng.chisquare(nu, size=(n_sims, 1)) / nu
        z = z / np.sqrt(g) * np.sqrt((nu - 2.0) / nu)
    pnl = (mu + z) @ w
    return historical_var_es(pnl, alpha)


@dataclass
class BacktestResult:
    n_obs: int
    n_exceptions: int
    expected: float
    lr_pof: float
    p_pof: float
    lr_ind: float
    p_ind: float
    lr_cc: float
    p_cc: float

    def passes(self, level: float = 0.05) -> bool:
        return self.p_cc > level


def _xlogy(x, y):
    return 0.0 if x == 0 else x * np.log(y)


def kupiec_pof(exceptions, alpha: float):
    """Kupiec (1995) proportion-of-failures likelihood ratio and p-value (chi2(1))."""
    e = np.asarray(exceptions, bool)
    T, x = e.size, int(e.sum())
    p = 1.0 - alpha
    phat = x / T
    ll0 = _xlogy(T - x, 1 - p) + _xlogy(x, p)
    ll1 = _xlogy(T - x, 1 - phat) + _xlogy(x, phat)
    lr = -2.0 * (ll0 - ll1)
    return float(lr), float(stats.chi2.sf(lr, 1))


def christoffersen(exceptions):
    """Christoffersen (1998) independence LR test (first-order Markov), chi2(1)."""
    e = np.asarray(exceptions, int)
    prev, curr = e[:-1], e[1:]
    n00 = int(np.sum((prev == 0) & (curr == 0)))
    n01 = int(np.sum((prev == 0) & (curr == 1)))
    n10 = int(np.sum((prev == 1) & (curr == 0)))
    n11 = int(np.sum((prev == 1) & (curr == 1)))
    pi01 = n01 / max(n00 + n01, 1)
    pi11 = n11 / max(n10 + n11, 1)
    pi = (n01 + n11) / max(n00 + n01 + n10 + n11, 1)
    ll0 = _xlogy(n00 + n10, 1 - pi) + _xlogy(n01 + n11, pi)
    ll1 = _xlogy(n00, 1 - pi01) + _xlogy(n01, pi01) + _xlogy(n10, 1 - pi11) + _xlogy(n11, pi11)
    lr = max(-2.0 * (ll0 - ll1), 0.0)
    return float(lr), float(stats.chi2.sf(lr, 1))


def backtest_var(returns, var_forecasts, alpha: float) -> BacktestResult:
    """Unconditional coverage, independence and conditional coverage tests."""
    r = np.asarray(returns, float)
    v = np.asarray(var_forecasts, float)
    exc = r < -v
    lr_pof, p_pof = kupiec_pof(exc, alpha)
    lr_ind, p_ind = christoffersen(exc)
    lr_cc = lr_pof + lr_ind
    return BacktestResult(
        n_obs=r.size,
        n_exceptions=int(exc.sum()),
        expected=float(r.size * (1 - alpha)),
        lr_pof=lr_pof,
        p_pof=p_pof,
        lr_ind=lr_ind,
        p_ind=p_ind,
        lr_cc=lr_cc,
        p_cc=float(stats.chi2.sf(lr_cc, 2)),
    )
