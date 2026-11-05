"""Alpha research: signals, evaluation, a planted-alpha test market, market making.

signals         order-book imbalance, microprice, OFI, trade-flow imbalance, past returns
evaluation      IC decay, Newey-West inference, purged walk-forward ridge, cost-aware
                backtest, probabilistic / deflated Sharpe ratio
simulate        synthetic order book with a known (or zero) alpha, used to validate the above
market_making   Avellaneda-Stoikov with inventory control and alpha-skewed quotes
data            Binance bookTicker / aggTrades loaders, as-of sampling onto a clock grid
"""

from . import data, evaluation, market_making, signals, simulate

__all__ = ["data", "evaluation", "market_making", "signals", "simulate"]
