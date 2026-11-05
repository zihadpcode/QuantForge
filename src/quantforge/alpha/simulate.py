"""Synthetic limit-order-book market with a *planted, known* alpha.

Why simulate?
-------------
An alpha-research pipeline has to answer two questions before it can be
trusted on real data:

1. **Power**: when a signal really predicts returns, does the pipeline find it
   and estimate its size correctly?
2. **Size (false positives)**: when *nothing* predicts returns, does the
   pipeline say so, instead of mining noise into a fake edge?

Neither question can be answered on real data, because there the true answer
is unknown. Here it is known by construction, so the test-suite can check both.

The model (one step = one clock tick, e.g. 100 ms)
--------------------------------------------------
* Best bid/ask queue sizes follow independent log-AR(1) processes, so the
  level-1 order-book imbalance ``I_t = (Qb - Qa) / (Qb + Qa)`` wanders in
  (-1, 1).
* A latent "informed flow" state ``z_t`` follows a persistent AR(1) with unit
  variance. It is **not observable**; it leaks into the tape through trade
  signs: each trade is buyer-initiated with probability ``(1 + kappa tanh z_t)/2``.
* The mid moves by one tick up/down with probabilities::

      P(up)   = p_move * (1 + a_t) / 2
      P(down) = p_move * (1 - a_t) / 2,    a_t = clip(beta I_t + gamma z_t, -1, 1)

  so the *true* one-step alpha is ``E[dmid_{t+1} | F_t] = p_move * a_t * tick``.
* The spread is always one tick (a "large-tick" asset such as BTC perpetuals or
  front-month index futures).

Setting ``beta = gamma = kappa = 0`` gives a market with zero alpha: the
"null" world used to measure the false-positive rate.

Simplifications (deliberate, documented): queues do not deplete/refill in
response to trades and price moves, and there is no queue position. The goal is
a ground-truth test bed for the statistics, not a market-microstructure model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from .data import BookSeries

__all__ = ["SyntheticBook", "simulate_book"]


@dataclass
class SyntheticBook(BookSeries):
    # E[mid_{t+1} - mid_t | F_t] / tick: the ground truth, unobservable in real markets
    true_alpha_ticks: np.ndarray | None = None


def _ar1(n, phi, sd_innov, rng):
    """Stationary AR(1) started from its stationary distribution, via lfilter."""
    e = rng.standard_normal(n) * sd_innov
    x0 = rng.standard_normal() * sd_innov / np.sqrt(1 - phi * phi)
    out, _ = signal.lfilter([1.0], [1.0, -phi], e, zi=[phi * x0])
    return out


def simulate_book(
    n_steps: int = 200_000,
    beta: float = 0.30,
    gamma: float = 0.30,
    kappa: float = 0.50,
    p_move: float = 0.15,
    phi_z: float = 0.995,
    phi_q: float = 0.97,
    sd_q: float = 0.25,
    mean_log_depth: float = 2.0,
    trade_rate: float = 1.5,
    tick: float = 0.01,
    s0: float = 100.0,
    seed: int | None = None,
) -> SyntheticBook:
    """Simulate the planted-alpha order book described in the module docstring."""
    rng = np.random.default_rng(seed)
    # queues
    qb = np.exp(mean_log_depth + _ar1(n_steps, phi_q, sd_q, rng))
    qa = np.exp(mean_log_depth + _ar1(n_steps, phi_q, sd_q, rng))
    imb = (qb - qa) / (qb + qa)
    # latent informed state, unit stationary variance
    z = _ar1(n_steps, phi_z, np.sqrt(1 - phi_z**2), rng)
    # trades during the step ending at t, informed by z_t
    n_tr = rng.poisson(trade_rate, n_steps)
    p_buy = 0.5 * (1.0 + kappa * np.tanh(z))
    buys = rng.binomial(n_tr, p_buy)
    sells = n_tr - buys
    # price moves from t to t+1 driven by information at t
    a = np.clip(beta * imb + gamma * z, -1.0, 1.0)
    u = rng.random(n_steps)
    p_up = p_move * (1 + a) / 2
    p_dn = p_move * (1 - a) / 2
    step = np.where(u < p_up, 1, np.where(u < p_up + p_dn, -1, 0))
    mid_ticks = np.concatenate([[0], np.cumsum(step[:-1])])  # mid_t uses moves up to t-1 -> t
    mid = s0 + tick * mid_ticks
    return SyntheticBook(
        bid=mid - tick / 2,
        ask=mid + tick / 2,
        bid_qty=qb,
        ask_qty=qa,
        buy_vol=buys.astype(float),
        sell_vol=sells.astype(float),
        tick=tick,
        true_alpha_ticks=p_move * a,
    )
