"""Alpha evaluation: the statistics a signal must survive before it is traded.

Pipeline
--------
1. **Forward returns** are measured mid-to-mid. Using trade prices would add
   bid-ask bounce, a spurious mean reversion that makes reversal signals look
   predictive.
2. **Information coefficient (IC)**: the correlation between the signal and the
   forward return, in Pearson and rank form, across horizons. This gives the
   IC *decay curve*, which shows how long the information lasts.
3. **Inference with overlapping returns.** h-step forward returns sampled every
   step overlap, so regression residuals are MA(h-1) and the OLS standard error
   is far too small. Newey-West (HAC) standard errors with Bartlett weights fix
   this.
4. **Walk-forward, purged and embargoed fitting.** Models are fitted only on
   the past, and training rows whose label window reaches into the test block
   are dropped. Otherwise the model sees the test period's prices: label
   leakage, the classic way to build a fake alpha.
5. **Costs.** A taker strategy pays half the spread plus a fee every time it
   trades. The break-even fee says whether the alpha survives.
6. **Multiple testing.** The Probabilistic and Deflated Sharpe ratios (Bailey &
   Lopez de Prado 2012, 2014) correct a Sharpe ratio for non-normal returns and
   for the number of strategies tried.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "forward_return_bps",
    "ols_newey_west",
    "ic_decay",
    "quantile_returns",
    "walk_forward_splits",
    "walk_forward_ridge",
    "oos_r2",
    "TakerResult",
    "taker_backtest",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    "expected_max_sharpe",
]


# ---------------------------------------------------------------------------
# returns and inference
# ---------------------------------------------------------------------------
def forward_return_bps(mid, horizon: int) -> np.ndarray:
    """``(mid_{t+h} - mid_t) / mid_t * 1e4``; NaN for the last ``h`` points."""
    mid = np.asarray(mid, float)
    out = np.full(mid.size, np.nan)
    out[:-horizon] = (mid[horizon:] - mid[:-horizon]) / mid[:-horizon] * 1e4
    return out


@dataclass
class OLSResult:
    intercept: float
    slope: float
    se_ols: float
    se_nw: float
    t_nw: float
    r2: float
    n: int


def ols_newey_west(y, x, lags: int) -> OLSResult:
    """OLS of ``y`` on ``[1, x]`` with Newey-West (Bartlett kernel) standard errors.

    ``S = G_0 + sum_{l=1}^{L} (1 - l/(L+1)) (G_l + G_l')``,
    ``G_l = sum_t g_t g_{t-l}'``, ``g_t = u_t x_t``;
    ``Cov(b) = (X'X)^{-1} S (X'X)^{-1}`` (no small-sample correction).
    """
    y, x = np.asarray(y, float), np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = y.size
    X = np.column_stack([np.ones(n), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ (X.T @ y)
    u = y - X @ b
    g = X * u[:, None]
    S = g.T @ g
    for lag in range(1, lags + 1):
        G = g[lag:].T @ g[:-lag]
        S += (1.0 - lag / (lags + 1.0)) * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se_ols = np.sqrt(u @ u / (n - 2) * XtX_inv[1, 1])
    se_nw = float(np.sqrt(cov[1, 1]))
    r2 = 1.0 - (u @ u) / np.sum((y - y.mean()) ** 2)
    return OLSResult(float(b[0]), float(b[1]), float(se_ols), se_nw, float(b[1] / se_nw), float(r2), int(n))


def ic_decay(sig, mid, horizons) -> list[dict]:
    """IC, rank IC, slope and Newey-West t-stat of ``sig`` for each horizon."""
    sig = np.asarray(sig, float)
    rows = []
    for h in horizons:
        fr = forward_return_bps(mid, h)
        m = np.isfinite(sig) & np.isfinite(fr)
        ic = float(np.corrcoef(sig[m], fr[m])[0, 1])
        ric = float(stats.spearmanr(sig[m], fr[m]).statistic)
        ols = ols_newey_west(fr[m], sig[m], lags=max(h, 1))
        rows.append(dict(horizon=h, n=int(m.sum()), ic=ic, rank_ic=ric, slope_bps=ols.slope, t_nw=ols.t_nw,
                         t_naive=ols.slope / ols.se_ols))
    return rows


def quantile_returns(sig, fwd, n_q: int = 10):
    """Mean forward return in each signal quantile (lowest to highest)."""
    sig, fwd = np.asarray(sig, float), np.asarray(fwd, float)
    m = np.isfinite(sig) & np.isfinite(fwd)
    s, f = sig[m], fwd[m]
    edges = np.quantile(s, np.linspace(0, 1, n_q + 1))
    idx = np.clip(np.searchsorted(edges, s, side="right") - 1, 0, n_q - 1)
    means = np.array([f[idx == i].mean() for i in range(n_q)])
    counts = np.bincount(idx, minlength=n_q)
    return means, counts


# ---------------------------------------------------------------------------
# walk-forward model fitting
# ---------------------------------------------------------------------------
def walk_forward_splits(n: int, n_folds: int, embargo: int, min_train: int):
    """Expanding-window splits: train = [0, start - embargo), test = [start, end).

    The embargo must be at least the label horizon so that no training label
    (which looks ``h`` steps ahead) overlaps the test block.
    """
    starts = np.linspace(min_train, n, n_folds + 1).astype(int)
    for a, b in zip(starts[:-1], starts[1:]):
        train_end = a - embargo
        if train_end <= 0:
            raise ValueError("embargo too large for min_train")
        yield np.arange(0, train_end), np.arange(a, b)


def walk_forward_ridge(X, y, horizon: int, n_folds: int = 5, lam: float = 1.0, min_train_frac: float = 0.2,
                       embargo: int | None = None):
    """Out-of-sample ridge forecasts of ``y`` from the columns of ``X``.

    Features are standardised with *training-fold* statistics only. Returns
    ``(yhat, coefs)`` where ``yhat`` is NaN outside the test blocks and
    ``coefs`` lists the standardised coefficients fitted for each fold.
    """
    X = np.atleast_2d(np.asarray(X, float))
    if X.shape[0] != np.asarray(y).size:
        X = X.T
    y = np.asarray(y, float)
    n, p = X.shape
    emb = horizon if embargo is None else embargo
    if emb < horizon:
        raise ValueError("embargo shorter than the label horizon leaks future prices into training")
    yhat = np.full(n, np.nan)
    coefs = []
    for tr, te in walk_forward_splits(n, n_folds, emb, int(min_train_frac * n)):
        ok = np.all(np.isfinite(X[tr]), axis=1) & np.isfinite(y[tr])
        Xt, yt = X[tr][ok], y[tr][ok]
        mu, sd = Xt.mean(axis=0), Xt.std(axis=0)
        sd[sd == 0] = 1.0
        Z = (Xt - mu) / sd
        ym = yt.mean()
        w = np.linalg.solve(Z.T @ Z + lam * np.eye(p), Z.T @ (yt - ym))
        coefs.append(w)
        Xe = X[te]
        good = np.all(np.isfinite(Xe), axis=1)
        yhat[te[good]] = ym + ((Xe[good] - mu) / sd) @ w
    return yhat, np.array(coefs)


def oos_r2(y, yhat) -> float:
    """Out-of-sample R^2 against the zero forecast: ``1 - SSE / sum(y^2)``."""
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    m = np.isfinite(y) & np.isfinite(yhat)
    return float(1.0 - np.sum((y[m] - yhat[m]) ** 2) / np.sum(y[m] ** 2))


# ---------------------------------------------------------------------------
# cost-aware backtest
# ---------------------------------------------------------------------------
@dataclass
class TakerResult:
    pnl_bps: np.ndarray  # net P&L per holding period, bps of notional
    gross_bps: np.ndarray
    n_periods: int
    n_trades: int  # number of rebalances where the position changed
    turnover: float  # total |position change|, in units of notional
    hit_rate: float  # fraction of periods with a position whose gross P&L > 0
    breakeven_fee_bps: float  # fee per unit traded that sets net P&L to zero

    @property
    def mean_net_bps(self) -> float:
        return float(self.pnl_bps.mean())

    @property
    def sharpe(self) -> float:
        sd = self.pnl_bps.std(ddof=1)
        return float(self.pnl_bps.mean() / sd) if sd > 0 else 0.0


def taker_backtest(forecast_bps, bid, ask, horizon: int, threshold_bps: float = 0.0, fee_bps: float = 0.0) -> TakerResult:
    """Trade the sign of the forecast with market orders, rebalancing every ``horizon`` steps.

    Position ``p_k = sign(f) * 1{|f| > threshold}`` (units of notional) is set at
    ``t_k = k h`` and held to ``t_{k+1}``. Trading ``|dp|`` units crosses the
    spread (cost: half-spread, since P&L is marked to mid) and pays
    ``fee_bps``. The position is flattened at the end.
    """
    f = np.asarray(forecast_bps, float)
    bid, ask = np.asarray(bid, float), np.asarray(ask, float)
    mid = 0.5 * (bid + ask)
    idx = np.arange(0, mid.size, horizon)
    if idx[-1] != mid.size - 1:
        idx = np.append(idx, mid.size - 1)
    fk = f[idx[:-1]]
    pos = np.where(np.isfinite(fk) & (np.abs(fk) > threshold_bps), np.sign(fk), 0.0)
    m0, m1 = mid[idx[:-1]], mid[idx[1:]]
    half_spread_bps = 0.5 * (ask - bid)[idx] / mid[idx] * 1e4
    prev = np.concatenate([[0.0], pos])
    dpos = np.abs(np.diff(np.concatenate([prev, [0.0]])))  # includes final flatten
    spread_cost = dpos * half_spread_bps
    gross = pos * (m1 - m0) / m0 * 1e4
    cost = spread_cost[:-1] + dpos[:-1] * fee_bps
    net = gross - cost
    net[-1] -= spread_cost[-1] + dpos[-1] * fee_bps  # final flatten
    turnover = float(dpos.sum())
    traded = pos != 0
    return TakerResult(
        pnl_bps=net,
        gross_bps=gross,
        n_periods=int(pos.size),
        n_trades=int((dpos[:-1] > 0).sum()),
        turnover=turnover,
        hit_rate=float((gross[traded] > 0).mean()) if traded.any() else float("nan"),
        breakeven_fee_bps=float((gross.sum() - spread_cost.sum()) / turnover) if turnover > 0 else float("nan"),
    )


# ---------------------------------------------------------------------------
# Sharpe-ratio inference under non-normality and multiple testing
# ---------------------------------------------------------------------------
def probabilistic_sharpe_ratio(returns, sr_benchmark: float = 0.0) -> float:
    """P(true per-period Sharpe > benchmark), Bailey & Lopez de Prado (2012).

    ``PSR = Phi( (SR - SR*) sqrt(T-1) / sqrt(1 - g3 SR + (g4 - 1)/4 SR^2) )``
    with sample skewness ``g3`` and (non-excess) kurtosis ``g4``.
    """
    r = np.asarray(returns, float)
    T = r.size
    sr = r.mean() / r.std(ddof=1)
    g3 = stats.skew(r)
    g4 = stats.kurtosis(r, fisher=False)
    den = np.sqrt(max(1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr * sr, 1e-12))
    return float(stats.norm.cdf((sr - sr_benchmark) * np.sqrt(T - 1) / den))


_EULER_GAMMA = 0.5772156649015329


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """Expected maximum of ``n_trials`` Sharpe ratios when every true Sharpe is 0.

    ``E[max] ~ sqrt(V) [(1 - g) Phi^-1(1 - 1/N) + g Phi^-1(1 - 1/(N e))]``,
    g = Euler-Mascheroni constant.
    """
    if n_trials <= 1:
        return 0.0
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(np.sqrt(sr_variance) * ((1 - _EULER_GAMMA) * z1 + _EULER_GAMMA * z2))


def deflated_sharpe_ratio(returns, n_trials: int, sr_variance: float) -> float:
    """PSR against the Sharpe you would expect from the best of ``n_trials`` pure-noise strategies."""
    return probabilistic_sharpe_ratio(returns, expected_max_sharpe(n_trials, sr_variance))
