"""Market-data containers and loaders.

Real data
---------
Binance publishes free historical files at https://data.binance.vision:

* ``futures/um/daily/bookTicker/<SYM>/<SYM>-bookTicker-<date>.zip``: every
  change of the best bid/ask (price and size). Columns:
  ``update_id, best_bid_price, best_bid_qty, best_ask_price, best_ask_qty,
  transaction_time, event_time`` (times in ms).
* ``.../aggTrades/...``: ``agg_trade_id, price, quantity, first_trade_id,
  last_trade_id, transact_time, is_buyer_maker``. ``is_buyer_maker = true``
  means the *seller* was the aggressor.

Event data is irregular, so it is sampled onto a fixed clock grid. The book
uses the last update at or before each grid time (an as-of join, never a
future update), and trades are summed over the interval ``(g_{i-1}, g_i]``.
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = ["BookSeries", "read_binance_csv", "book_from_events", "load_binance"]

BOOKTICKER_COLS = ["update_id", "best_bid_price", "best_bid_qty", "best_ask_price", "best_ask_qty",
                   "transaction_time", "event_time"]
AGGTRADES_COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time",
                  "is_buyer_maker"]


@dataclass
class BookSeries:
    """Top-of-book + trade flow on a regular clock grid."""

    bid: np.ndarray
    ask: np.ndarray
    bid_qty: np.ndarray
    ask_qty: np.ndarray
    buy_vol: np.ndarray
    sell_vol: np.ndarray
    tick: float
    time_ms: np.ndarray | None = None

    @property
    def mid(self) -> np.ndarray:
        return 0.5 * (self.bid + self.ask)

    def __len__(self) -> int:
        return self.bid.size


def read_binance_csv(path, columns: list[str]) -> dict[str, np.ndarray]:
    """Read a Binance CSV (optionally inside a .zip), with or without a header row."""
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            text = zf.read(zf.namelist()[0]).decode()
    else:
        text = path.read_text()
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    if any(c in header for c in columns):
        names, body = header, rows[1:]
    else:
        names, body = columns, rows
    data = {}
    for j, name in enumerate(names):
        col = [r[j] for r in body]
        if name == "is_buyer_maker":
            data[name] = np.array([v.strip().lower() == "true" for v in col])
        else:
            data[name] = np.array(col, dtype=float)
    return data


def book_from_events(
    book_time_ms, bid, ask, bid_qty, ask_qty,
    trade_time_ms=None, trade_qty=None, trade_is_buyer_maker=None,
    step_ms: int = 100, tick: float | None = None,
) -> BookSeries:
    """Sample event-time quotes and trades onto a regular grid without look-ahead."""
    t = np.asarray(book_time_ms, float)
    order = np.argsort(t, kind="stable")
    t = t[order]
    bid, ask = np.asarray(bid, float)[order], np.asarray(ask, float)[order]
    bq, aq = np.asarray(bid_qty, float)[order], np.asarray(ask_qty, float)[order]
    start = np.ceil(t[0] / step_ms) * step_ms
    grid = np.arange(start, t[-1] + 1e-9, step_ms)
    j = np.searchsorted(t, grid, side="right") - 1  # last update with time <= grid time
    buy = np.zeros(grid.size)
    sell = np.zeros(grid.size)
    if trade_time_ms is not None:
        tt = np.asarray(trade_time_ms, float)
        qty = np.asarray(trade_qty, float)
        seller_aggr = np.asarray(trade_is_buyer_maker, bool)
        # trade at time tt belongs to the first grid point >= tt: interval (g_{i-1}, g_i]
        b = np.searchsorted(grid, tt, side="left")
        # keep trades inside (g_0 - step, g_last]; earlier trades predate the first quote
        ok = (b < grid.size) & (tt > grid[0] - step_ms)
        np.add.at(buy, b[ok & ~seller_aggr], qty[ok & ~seller_aggr])
        np.add.at(sell, b[ok & seller_aggr], qty[ok & seller_aggr])
    if tick is None:
        diffs = np.abs(np.diff(np.concatenate([bid, ask])))
        diffs = diffs[diffs > 1e-12]
        tick = float(np.round(diffs.min(), 10)) if diffs.size else float("nan")
    return BookSeries(bid=bid[j], ask=ask[j], bid_qty=bq[j], ask_qty=aq[j], buy_vol=buy, sell_vol=sell,
                      tick=tick, time_ms=grid)


def load_binance(bookticker_path, aggtrades_path=None, step_ms: int = 100, tick: float | None = None) -> BookSeries:
    """Load Binance bookTicker (+ optional aggTrades) files onto a clock grid."""
    bk = read_binance_csv(bookticker_path, BOOKTICKER_COLS)
    kw = {}
    if aggtrades_path is not None:
        tr = read_binance_csv(aggtrades_path, AGGTRADES_COLS)
        kw = dict(trade_time_ms=tr["transact_time"], trade_qty=tr["quantity"],
                  trade_is_buyer_maker=tr["is_buyer_maker"])
    return book_from_events(bk["transaction_time"], bk["best_bid_price"], bk["best_ask_price"],
                            bk["best_bid_qty"], bk["best_ask_qty"], step_ms=step_ms, tick=tick, **kw)
