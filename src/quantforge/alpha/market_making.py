"""Market making with inventory control and an alpha signal.

Avellaneda & Stoikov (2008)
---------------------------
A dealer with CARA utility (risk aversion ``gamma``) quotes around a mid price
``dS = sigma dW``. Market orders arrive at a quote placed ``delta`` away from
the mid with Poisson intensity ``lambda(delta) = A exp(-k delta)``. The
(approximately) optimal quotes are:

    reservation price  r = s - q gamma sigma^2 (T - t)
    total spread       delta_a + delta_b = gamma sigma^2 (T - t) + (2/gamma) ln(1 + gamma/k)

With a long inventory ``q > 0`` the dealer lowers both quotes: it sells more
readily and buys less, pulling inventory back to zero.

Adding alpha
------------
If the mid has a predictable drift ``alpha_t`` (an OU process with mean
reversion ``theta``), the expected mid at the horizon is
``s + alpha (1 - e^{-theta tau}) / theta``. The certainty-equivalent quote
centre becomes

    r = s + alpha_hat (1 - e^{-theta tau}) / theta - q gamma sigma^2 tau

This is the structure of the optimal controls in Cartea, Jaimungal & Ricci
(2014), here used as a heuristic. Informed order flow (buyers arrive faster
when ``alpha > 0``) is modelled as ``lambda_a = A e^{-k delta_a + c alpha}`` and
``lambda_b = A e^{-k delta_b - c alpha}``. That is adverse selection: a dealer
blind to alpha sells just before the price rises.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["MMResult", "simulate_market_maker"]


@dataclass
class MMResult:
    pnl: np.ndarray  # terminal P&L per simulation (cash + inventory marked to mid)
    final_q: np.ndarray
    n_fills: np.ndarray
    mean_spread: float

    @property
    def mean(self) -> float:
        return float(self.pnl.mean())

    @property
    def std(self) -> float:
        return float(self.pnl.std(ddof=1))

    @property
    def sharpe(self) -> float:
        return self.mean / self.std

    def summary(self) -> dict:
        return dict(mean_pnl=self.mean, std_pnl=self.std, sharpe=self.sharpe,
                    mean_final_q=float(self.final_q.mean()), std_final_q=float(self.final_q.std(ddof=1)),
                    mean_fills=float(self.n_fills.mean()), mean_spread=self.mean_spread)


def simulate_market_maker(
    strategy: str = "inventory",
    n_sims: int = 1000,
    T: float = 1.0,
    dt: float = 0.005,
    s0: float = 100.0,
    sigma: float = 2.0,
    gamma: float = 0.1,
    k: float = 1.5,
    A: float = 140.0,
    alpha_sd: float = 0.0,
    alpha_theta: float = 5.0,
    informed: float = 0.0,
    signal_corr: float = 1.0,
    seed: int | None = None,
) -> MMResult:
    """Monte Carlo of a single-asset market maker.

    strategy:
        ``"symmetric"`` - quotes centred on the mid with the AS spread;
        ``"inventory"`` - Avellaneda-Stoikov reservation price;
        ``"alpha"``     - AS plus the alpha shift of the reservation price.

    With ``alpha_sd = informed = 0`` this is exactly the experiment of
    Avellaneda & Stoikov (2008), Section 4 (binomial mid moves ``+-sigma
    sqrt(dt)``). ``signal_corr`` < 1 makes the dealer see only the conditional
    expectation of alpha given a noisy signal with that correlation.

    All strategies share the same random numbers (common random numbers), so
    differences between them are not sampling noise.
    """
    if strategy not in ("symmetric", "inventory", "alpha"):
        raise ValueError("strategy must be 'symmetric', 'inventory' or 'alpha'")
    rng = np.random.default_rng(seed)
    n_steps = int(round(T / dt))
    s = np.full(n_sims, s0)
    q = np.zeros(n_sims)
    cash = np.zeros(n_sims)
    fills = np.zeros(n_sims)
    alpha = rng.standard_normal(n_sims) * alpha_sd
    a_decay = np.exp(-alpha_theta * dt)
    a_innov = alpha_sd * np.sqrt(1.0 - a_decay**2)
    spread_const = (2.0 / gamma) * np.log(1.0 + gamma / k)
    spread_sum = 0.0

    for i in range(n_steps):
        tau = T - i * dt
        spread = gamma * sigma**2 * tau + spread_const
        spread_sum += spread
        # draw every random number every step, whatever the strategy, so all
        # strategies see identical markets (common random numbers)
        noise = rng.standard_normal(n_sims) if alpha_sd > 0 else None
        u_a, u_b, u_s = rng.random(n_sims), rng.random(n_sims), rng.random(n_sims)
        a_shock = rng.standard_normal(n_sims) if alpha_sd > 0 else None

        if strategy == "symmetric":
            r = s
        else:
            r = s - q * gamma * sigma**2 * tau
            if strategy == "alpha" and alpha_sd > 0:
                a_hat = signal_corr**2 * alpha + signal_corr * np.sqrt(1 - signal_corr**2) * alpha_sd * noise
                r = r + a_hat * (1.0 - np.exp(-alpha_theta * tau)) / alpha_theta
        ask, bid = r + spread / 2.0, r - spread / 2.0
        delta_a, delta_b = ask - s, s - bid

        lam_a = A * np.exp(-k * delta_a + informed * alpha)
        lam_b = A * np.exp(-k * delta_b - informed * alpha)
        hit_a = u_a < np.minimum(lam_a * dt, 1.0)
        hit_b = u_b < np.minimum(lam_b * dt, 1.0)
        q += hit_b.astype(float) - hit_a.astype(float)
        cash += hit_a * ask - hit_b * bid
        fills += hit_a + hit_b

        # mid moves: drift + binomial shock (AS 2008 uses a +-sigma sqrt(dt) binomial)
        s = s + alpha * dt + np.where(u_s < 0.5, 1.0, -1.0) * sigma * np.sqrt(dt)
        if alpha_sd > 0:
            alpha = alpha * a_decay + a_innov * a_shock

    return MMResult(pnl=cash + q * s, final_q=q, n_fills=fills, mean_spread=spread_sum / n_steps)
