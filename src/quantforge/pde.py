"""Finite-difference solver for the Black-Scholes PDE.

Solves ``V_tau = sigma^2/2 V_xx + (r - q - sigma^2/2) V_x - r V`` in log-price
``x = ln S`` with:

* Crank-Nicolson time stepping with Rannacher start-up (the first steps are
  replaced by implicit-Euler half steps, damping the spurious oscillations CN
  produces from the non-smooth payoff);
* early exercise via the penalty method of Forsyth & Vetzal (2002), iterated to
  a fixed active set at every step (quadratic convergence, no PSOR sweeps);
* optional continuously monitored knock-out barriers, imposed as zero
  Dirichlet conditions on the barrier.

Every linear solve is tridiagonal and done with a banded LAPACK solver.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.linalg import solve_banded

__all__ = ["PDEResult", "bs_pde"]


@dataclass
class PDEResult:
    price: float
    delta: float
    gamma: float
    S_grid: np.ndarray
    V_grid: np.ndarray
    penalty_iterations: int


def bs_pde(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    is_call: bool = True,
    american: bool = False,
    lower_barrier: float | None = None,
    upper_barrier: float | None = None,
    n_space: int = 800,
    n_time: int = 800,
    n_sd: float = 6.0,
    rannacher_steps: int = 2,
    penalty: float = 1e8,
) -> PDEResult:
    """Price a vanilla / American / knock-out option on a uniform log grid."""
    if american and (lower_barrier is not None or upper_barrier is not None):
        raise ValueError("American barrier options are not supported")
    x0 = np.log(S0)
    half_width = n_sd * sigma * np.sqrt(T)
    x_min = min(x0, np.log(K)) - half_width
    x_max = max(x0, np.log(K)) + half_width
    if lower_barrier is not None:
        if S0 <= lower_barrier:
            raise ValueError("spot is already at/below the lower barrier")
        x_min = np.log(lower_barrier)
    if upper_barrier is not None:
        if S0 >= upper_barrier:
            raise ValueError("spot is already at/above the upper barrier")
        x_max = np.log(upper_barrier)

    x = np.linspace(x_min, x_max, n_space + 1)
    dx = x[1] - x[0]
    S = np.exp(x)
    w = 1.0 if is_call else -1.0
    payoff = np.maximum(w * (S - K), 0.0)

    a = 0.5 * sigma**2
    b = r - q - 0.5 * sigma**2
    lo = a / dx**2 - b / (2 * dx)
    di = -2 * a / dx**2 - r
    up = a / dx**2 + b / (2 * dx)
    M = n_space + 1

    def boundary(tau):
        dfr, dfq = np.exp(-r * tau), np.exp(-q * tau)
        if lower_barrier is not None:
            left = 0.0
        elif is_call:
            left = 0.0
        else:
            left = max(K * dfr - S[0] * dfq, 0.0)
            if american:
                left = max(left, K - S[0])
        if upper_barrier is not None:
            right = 0.0
        elif is_call:
            right = max(S[-1] * dfq - K * dfr, 0.0)
            if american:
                right = max(right, S[-1] - K)
        else:
            right = 0.0
        return left, right

    def L_apply(V):
        out = np.zeros_like(V)
        out[1:-1] = lo * V[:-2] + di * V[1:-1] + up * V[2:]
        return out

    def lhs_banded(theta_dt):
        ab = np.zeros((3, M))
        ab[1, :] = 1.0 - theta_dt * di
        ab[0, 2:] = -theta_dt * up
        ab[2, :-2] = -theta_dt * lo
        # Dirichlet rows
        ab[1, 0] = ab[1, -1] = 1.0
        ab[0, 1] = 0.0
        ab[2, -2] = 0.0
        return ab

    # time steps: Rannacher -> 2 implicit half steps per replaced CN step
    dt = T / n_time
    steps = [(0.5 * dt, 1.0)] * (2 * rannacher_steps) + [(dt, 0.5)] * (n_time - rannacher_steps)

    V = payoff.copy()
    if lower_barrier is not None:
        V[0] = 0.0
    if upper_barrier is not None:
        V[-1] = 0.0
    tau = 0.0
    total_pen_iter = 0
    cache: dict = {}
    for h, theta in steps:
        tau += h
        key = (h, theta)
        if key not in cache:
            cache[key] = lhs_banded(theta * h)
        ab = cache[key]
        rhs = V + (1.0 - theta) * h * L_apply(V)
        left, right = boundary(tau)
        rhs[0], rhs[-1] = left, right
        V_new = solve_banded((1, 1), ab, rhs)
        if american:
            active = np.zeros(M, dtype=bool)
            for _ in range(100):
                new_active = V_new < payoff
                new_active[[0, -1]] = False
                if np.array_equal(new_active, active):
                    break
                active = new_active
                pen = np.where(active, penalty, 0.0)
                ab_p = ab.copy()
                ab_p[1, :] += pen
                V_new = solve_banded((1, 1), ab_p, rhs + pen * payoff)
                total_pen_iter += 1
        V = V_new

    spline = CubicSpline(x, V)
    v0 = float(spline(x0))
    vx, vxx = float(spline(x0, 1)), float(spline(x0, 2))
    return PDEResult(
        price=v0,
        delta=vx / S0,
        gamma=(vxx - vx) / S0**2,
        S_grid=S,
        V_grid=V,
        penalty_iterations=total_pen_iter,
    )
