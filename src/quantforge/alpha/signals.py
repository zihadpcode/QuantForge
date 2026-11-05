"""High-frequency alpha signals from the order book and the tape.

Every signal at index ``t`` uses only information available at the end of
step ``t``: no look-ahead. The test-suite enforces this by perturbing the future
and checking that past signal values do not change.

Formulas
--------
Order-book imbalance (level 1)::

    I_t = (Qb_t - Qa_t) / (Qb_t + Qa_t)                      in (-1, 1)

Microprice (size-weighted mid; Stoikov 2018 gives its exact martingale form)::

    P_micro = (Pa Qb + Pb Qa) / (Qb + Qa)
    micro_dev_bps = (P_micro - mid) / mid * 1e4 = I * (spread / 2) / mid * 1e4

  With a constant one-tick spread this is a rescaled I: same information.

Order-flow imbalance (Cont, Kukanov & Stoikov 2014), per update n::

    e_n =  Qb_n 1{Pb_n >= Pb_{n-1}} - Qb_{n-1} 1{Pb_n <= Pb_{n-1}}
         - Qa_n 1{Pa_n <= Pa_{n-1}} + Qa_{n-1} 1{Pa_n >= Pa_{n-1}}
    OFI_t(w) = sum of e_n over the last w updates, divided by a causal EWMA of depth

  It nets the demand added at the bid against supply added at the ask,
  including the queues that vanish when a price level is crossed.

Trade-flow imbalance over a window ``w``::

    TFI_t(w) = (sum buy_vol - sum sell_vol) / (sum buy_vol + sum sell_vol)

Past mid return (short-term momentum (+) or reversal (-))::

    R_t(w) = (mid_t - mid_{t-w}) / mid_{t-w} * 1e4    [bps]
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "book_imbalance",
    "microprice",
    "microprice_deviation_bps",
    "order_flow_imbalance",
    "trade_flow_imbalance",
    "past_return_bps",
    "rolling_sum",
    "ewma",
    "zscore_trailing",
]


def rolling_sum(x, w: int) -> np.ndarray:
    """Trailing sum over the last ``w`` observations (inclusive); NaN until full."""
    x = np.asarray(x, float)
    c = np.concatenate([[0.0], np.cumsum(x)])
    out = np.full(x.size, np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


def ewma(x, halflife: float) -> np.ndarray:
    """Causal exponentially weighted mean, ``m_t = (1-a) m_{t-1} + a x_t``."""
    from scipy import signal as _sig

    a = 1.0 - 0.5 ** (1.0 / halflife)
    x = np.asarray(x, float)
    y, _ = _sig.lfilter([a], [1.0, -(1.0 - a)], x, zi=[(1.0 - a) * x[0]])
    return y


def zscore_trailing(x, window: int) -> np.ndarray:
    """Causal z-score using mean/sd of the *previous* ``window`` values (excludes t)."""
    x = np.asarray(x, float)
    s1 = rolling_sum(x, window)
    s2 = rolling_sum(x * x, window)
    mu = np.concatenate([[np.nan], (s1 / window)[:-1]])
    var = np.concatenate([[np.nan], (s2 / window)[:-1]]) - mu**2
    with np.errstate(invalid="ignore", divide="ignore"):
        return (x - mu) / np.sqrt(np.maximum(var, 1e-300))


def book_imbalance(bid_qty, ask_qty) -> np.ndarray:
    qb, qa = np.asarray(bid_qty, float), np.asarray(ask_qty, float)
    return (qb - qa) / (qb + qa)


def microprice(bid, ask, bid_qty, ask_qty) -> np.ndarray:
    bid, ask = np.asarray(bid, float), np.asarray(ask, float)
    qb, qa = np.asarray(bid_qty, float), np.asarray(ask_qty, float)
    return (ask * qb + bid * qa) / (qb + qa)


def microprice_deviation_bps(bid, ask, bid_qty, ask_qty) -> np.ndarray:
    mid = 0.5 * (np.asarray(bid, float) + np.asarray(ask, float))
    return (microprice(bid, ask, bid_qty, ask_qty) - mid) / mid * 1e4


def order_flow_imbalance(bid, ask, bid_qty, ask_qty, window: int = 1, normalize: bool = True,
                         depth_halflife: float = 500.0) -> np.ndarray:
    """Cont-Kukanov-Stoikov OFI summed over a trailing window of updates.

    With ``normalize`` the sum is divided by a *causal* EWMA of the average
    top-of-book depth (half-life ``depth_halflife`` updates), making it
    comparable across assets and regimes. Dividing by a full-sample mean depth
    instead would be look-ahead: today's signal would depend on future books.
    """
    pb, pa = np.asarray(bid, float), np.asarray(ask, float)
    qb, qa = np.asarray(bid_qty, float), np.asarray(ask_qty, float)
    e = np.full(pb.size, np.nan)
    e[1:] = (
        qb[1:] * (pb[1:] >= pb[:-1])
        - qb[:-1] * (pb[1:] <= pb[:-1])
        - qa[1:] * (pa[1:] <= pa[:-1])
        + qa[:-1] * (pa[1:] >= pa[:-1])
    )
    e0 = np.nan_to_num(e)
    out = rolling_sum(e0, window)
    out[:window] = np.nan  # first update has no predecessor
    if normalize:
        out = out / ewma(0.5 * (qb + qa), depth_halflife)
    return out


def trade_flow_imbalance(buy_vol, sell_vol, window: int) -> np.ndarray:
    b = rolling_sum(buy_vol, window)
    s = rolling_sum(sell_vol, window)
    tot = b + s
    out = np.zeros(tot.size)
    ok = tot > 0  # NaN compares False
    out[ok] = (b[ok] - s[ok]) / tot[ok]
    out[np.isnan(tot)] = np.nan
    return out


def past_return_bps(mid, window: int) -> np.ndarray:
    mid = np.asarray(mid, float)
    out = np.full(mid.size, np.nan)
    out[window:] = (mid[window:] - mid[:-window]) / mid[:-window] * 1e4
    return out
