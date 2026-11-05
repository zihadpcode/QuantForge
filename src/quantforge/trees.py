"""Binomial lattices: Cox-Ross-Rubinstein and Leisen-Reimer.

Leisen-Reimer (1996) chooses the up-probabilities by a Peizer-Pratt inversion
of the Black-Scholes ``d1``/``d2`` so that the tree is centred on the strike.
European prices then converge at O(1/N^2) without the odd/even oscillation of
CRR, which makes it the lattice of choice for American options.
"""

from __future__ import annotations

import numpy as np

from .blackscholes import d1_d2

__all__ = ["binomial_price"]


def _peizer_pratt(z: float, n: int) -> float:
    return 0.5 + np.sign(z) * 0.5 * np.sqrt(
        1.0 - np.exp(-((z / (n + 1.0 / 3.0 + 0.1 / (n + 1.0))) ** 2) * (n + 1.0 / 6.0))
    )


def binomial_price(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    is_call: bool = True,
    american: bool = False,
    n_steps: int = 501,
    method: str = "lr",
    exercise_dates: int | None = None,
) -> float:
    """Price a European/American/Bermudan vanilla on a recombining binomial tree.

    ``exercise_dates`` (with ``american=True``) restricts early exercise to
    ``exercise_dates`` equally spaced dates ``T i / exercise_dates`` (a Bermudan
    option); ``n_steps`` must then be a multiple of it, which in turn requires
    ``method='crr'`` because Leisen-Reimer needs an odd step count.
    """
    stride = None
    if exercise_dates is not None and american:
        if method != "crr" or n_steps % exercise_dates:
            raise ValueError("Bermudan pricing needs method='crr' and n_steps divisible by exercise_dates")
        stride = n_steps // exercise_dates
    dt = T / n_steps
    growth = np.exp((r - q) * dt)
    if method == "crr":
        u = np.exp(sigma * np.sqrt(dt))
        d = 1.0 / u
        p = (growth - d) / (u - d)
    elif method == "lr":
        if n_steps % 2 == 0:
            n_steps += 1  # LR is defined for odd N
            dt = T / n_steps
            growth = np.exp((r - q) * dt)
        d1, d2 = d1_d2(S0, K, T, r, sigma, q)
        p = _peizer_pratt(float(d2), n_steps)
        p_bar = _peizer_pratt(float(d1), n_steps)
        u = growth * p_bar / p
        d = (growth - p * u) / (1.0 - p)
    else:
        raise ValueError("method must be 'crr' or 'lr'")
    if not 0.0 < p < 1.0:
        raise ValueError("risk-neutral probability outside (0,1); increase n_steps")

    disc = np.exp(-r * dt)
    w = 1.0 if is_call else -1.0
    j = np.arange(n_steps + 1)
    S = S0 * u**j * d ** (n_steps - j)
    V = np.maximum(w * (S - K), 0.0)
    for n in range(n_steps - 1, -1, -1):
        V = disc * (p * V[1 : n + 2] + (1.0 - p) * V[: n + 1])
        if american and (stride is None or (n % stride == 0 and n > 0)):
            S = S0 * u ** j[: n + 1] * d ** (n - j[: n + 1])
            V = np.maximum(V, w * (S - K))
    return float(V[0])
