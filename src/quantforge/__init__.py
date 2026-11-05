"""quantforge: derivatives pricing, volatility surfaces and quantitative risk.

Modules
-------
blackscholes  closed-form BSM prices and Greeks (incl. 2nd-order)
implied_vol   vectorised, safeguarded-Newton implied volatility
fourier       COS and Lewis characteristic-function pricers
heston        Heston model: pricing, calibration, QE Monte Carlo
svi           raw SVI / SSVI fitting and static-arbitrage diagnostics
localvol      Dupire local volatility and local-vol Monte Carlo
pde           Crank-Nicolson PDE (American via penalty, barriers)
trees         CRR / Leisen-Reimer binomial lattices (Euro/American/Bermudan)
exotics       closed forms: geometric Asian, barrier options
montecarlo    MC engine: antithetic, control variates, RQMC, LSM
rates         curve bootstrapping, Nelson-Siegel-Svensson, Vasicek, CIR
risk          VaR / ES (historical, parametric, Cornish-Fisher, MC), backtests
garch         GARCH(1,1) QMLE, forecasting, simulation
portfolio     mean-variance, risk parity, Ledoit-Wolf shrinkage
"""

from . import (
    blackscholes,
    exotics,
    fourier,
    garch,
    heston,
    implied_vol,
    localvol,
    montecarlo,
    pde,
    portfolio,
    rates,
    risk,
    svi,
    trees,
)

__version__ = "1.0.0"

__all__ = [
    "blackscholes",
    "exotics",
    "fourier",
    "garch",
    "heston",
    "implied_vol",
    "localvol",
    "montecarlo",
    "pde",
    "portfolio",
    "rates",
    "risk",
    "svi",
    "trees",
]
