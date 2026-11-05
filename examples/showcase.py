"""Reproduce every figure and benchmark table in the README.

    python examples/showcase.py            # writes docs/figures/*.png and docs/RESULTS.md

All randomness is seeded, so the output is deterministic.
"""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from quantforge import blackscholes as bs
from quantforge.exotics import down_barrier_call, geometric_asian
from quantforge.garch import GarchParams, fit_garch, simulate_garch
from quantforge.heston import HestonParams, calibrate_heston, heston_price, simulate_heston_qe
from quantforge.implied_vol import implied_vol
from quantforge.localvol import dupire_local_vol, simulate_local_vol
from quantforge.montecarlo import asian_mc, barrier_mc, european_mc, longstaff_schwartz
from quantforge.pde import bs_pde
from quantforge.portfolio import efficient_frontier, min_variance, risk_parity, tangency
from quantforge.risk import backtest_var
from quantforge.svi import SSVI, fit_raw_svi
from quantforge.trees import binomial_price

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# ---- styling: one validated categorical order, one sequential ramp ---------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE_ORDINAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.labelsize": 10, "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2.0,
    "font.family": "DejaVu Sans",
})

rows: list[tuple[str, str, str, str]] = []  # (problem, quantforge, reference, source)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=160)
    plt.close(fig)
    print(f"  wrote docs/figures/{name}")


def section(t):
    print(f"\n== {t}")


# ============================================================================
section("Heston: benchmark, calibration and SVI fit")
FO = HestonParams(0.0175, 1.5768, 0.0398, 0.5751, -0.5711)
cos_v = heston_price(FO, 100, 100, 1.0, 0, 0)
lew_v = heston_price(FO, 100, 100, 1.0, 0, 0, method="lewis")
rows.append(("Heston ATM call, COS method", f"{cos_v:.9f}", "5.785155450", "Fang & Oosterlee (2008)"))
rows.append(("Heston ATM call, Lewis quadrature", f"{lew_v:.9f}", "5.785155450", "Fang & Oosterlee (2008)"))
ST = simulate_heston_qe(FO, 100, 1.0, 0, 0, n_steps=100, n_paths=400_000, seed=1)
pay = np.maximum(ST - 100, 0)
rows.append(("Heston ATM call, QE Monte Carlo (400k paths)", f"{pay.mean():.4f} ± {1.96 * pay.std() / np.sqrt(pay.size):.4f}",
             "5.785155450", "Andersen (2008) scheme"))

S, r, q = 100.0, 0.03, 0.01
true = HestonParams(0.03, 2.5, 0.05, 0.6, -0.7)
Ts = np.array([0.1, 0.25, 0.5, 1.0, 2.0])
Ks = np.linspace(70, 140, 15)
KK, TT = np.meshgrid(Ks, Ts)
F = S * np.exp((r - q) * TT)
cp = KK >= F
mkt = heston_price(true, S, KK, TT, r, q, cp)
t0 = time.perf_counter()
cal = calibrate_heston(S, r, q, KK, TT, mkt, cp, x0=HestonParams(0.04, 1.0, 0.04, 0.3, -0.3))
dt_cal = time.perf_counter() - t0
rows.append(("Heston calibration, 75 quotes: IV RMSE", f"{cal.iv_rmse:.1e} ({dt_cal:.1f}s, {cal.nfev} evals)", "0",
             "self-consistency"))
iv = implied_vol(mkt, S, KK, TT, r, q, cp)

fig, ax = plt.subplots(figsize=(7.2, 4.4))
for i, T in enumerate(Ts):
    k = np.log(Ks / F[i])
    fit = fit_raw_svi(k, iv[i], T)
    kk = np.linspace(k.min() - 0.05, k.max() + 0.05, 200)
    c = BLUE_ORDINAL[i + 1]
    ax.plot(kk, 100 * fit.params.implied_vol(kk, T), color=c, lw=2, label=f"T = {T:g}y  (SVI rmse {1e4 * fit.rmse_iv:.1f}bp)")
    ax.plot(k, 100 * iv[i], "o", ms=5, color=c, mec=SURFACE, mew=1.5)
ax.set_xlabel("log-moneyness  ln(K / F)")
ax.set_ylabel("implied volatility (%)")
ax.set_title("Heston smiles (dots) and raw-SVI fits (lines)")
ax.legend(loc="upper right")
save(fig, "svi_fit.png")

# ============================================================================
section("COS convergence")
fig, ax = plt.subplots(figsize=(7.2, 4.0))
Ns = np.array([16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024])
for i, T in enumerate([0.1, 1.0, 5.0]):
    ref = heston_price(FO, 100, np.array([80.0, 100.0, 120.0]), T, 0, 0, method="lewis")
    err = [np.abs(heston_price(FO, 100, np.array([80.0, 100.0, 120.0]), T, 0, 0, N=n, L=40) - ref).max() for n in Ns]
    ax.semilogy(Ns, np.maximum(err, 1e-16), "-o", ms=4, color=SERIES[i], label=f"T = {T:g}y")
ax.axhline(1e-8, color=MUTED, lw=1, ls="--")
ax.set_xlabel("number of cosine terms N")
ax.set_ylabel("max abs price error vs Lewis")
ax.set_title("COS method: exponential convergence (L = 40)")
ax.legend()
save(fig, "cos_convergence.png")

# ============================================================================
section("Dupire local vol")
surf = SSVI.heston_like(v0=0.04, v_inf=0.06, kappa=2.0, rho=-0.7, eta=1.0, gamma=0.4)
kg = np.linspace(-0.6, 0.4, 121)
tg = np.linspace(0.05, 3.0, 100)
KG, TG = np.meshgrid(kg, tg)
LV = dupire_local_vol(surf.total_variance, KG, TG)
IVs = surf.implied_vol(KG, TG)
fig, axes = plt.subplots(1, 2, figsize=(10, 4.0), sharey=True)
for ax, Z, ttl in ((axes[0], IVs, "SSVI implied vol"), (axes[1], LV, "Dupire local vol")):
    pcm = ax.pcolormesh(KG, TG, 100 * Z, cmap="Blues", vmin=10, vmax=55, shading="auto")
    cs = ax.contour(KG, TG, 100 * Z, levels=[15, 20, 25, 30, 40], colors=INK2, linewidths=0.8)
    ax.clabel(cs, fmt="%d%%", fontsize=8)
    ax.set_title(ttl)
    ax.set_xlabel("log-moneyness k")
    ax.grid(False)
axes[0].set_ylabel("maturity T (years)")
fig.colorbar(pcm, ax=axes, label="volatility (%)", shrink=0.9)
fig.savefig(FIG / "local_vol.png", dpi=160)
plt.close(fig)
print("  wrote docs/figures/local_vol.png")

LT = simulate_local_vol(surf.total_variance, S, 1.0, r, q, n_steps=200, n_paths=200_000, seed=3)
Fw = S * np.exp((r - q) * 1.0)
worst_z = 0.0
for K in (75.0, 90.0, 100.0, 110.0, 125.0):
    call = K >= Fw
    ref = bs.price(S, K, 1.0, r, surf.implied_vol(np.log(K / Fw), 1.0), q, call)
    p = np.exp(-r) * np.maximum((LT - K) if call else (K - LT), 0)
    worst_z = max(worst_z, abs(p.mean() - ref) / (p.std() / np.sqrt(p.size)))
rows.append(("Local-vol MC reprices SSVI vanillas, 5 strikes", f"max abs z-score {worst_z:.2f}", "≈ N(0,1) noise",
             "Dupire (1994) / Gatheral (2006)"))

# ============================================================================
section("Monte Carlo variance reduction")
ref = bs.price(100, 100, 1, 0.05, 0.2)
Ps = 2 ** np.arange(10, 19, 2)
methods = [("plain MC", dict()), ("antithetic", dict(antithetic=True)),
           ("control variate", dict(control_variate=True)), ("randomised QMC (Sobol)", dict(method="sobol"))]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for i, (lab, kw) in enumerate(methods):
    rmse = []
    for n in Ps:
        est = [european_mc(100, 100, 1, 0.05, 0.2, n_paths=int(n), seed=1000 * s + 7, **kw).price for s in range(40)]
        rmse.append(np.sqrt(np.mean((np.array(est) - ref) ** 2)))
    ax.loglog(Ps, rmse, "-o", ms=5, color=SERIES[i], label=lab)
ax.loglog(Ps, 15 / np.sqrt(Ps), color=MUTED, lw=1, ls="--", label=r"$\propto N^{-1/2}$")
ax.set_xlabel("paths N")
ax.set_ylabel("RMSE vs Black-Scholes (40 runs)")
ax.set_title("European call: error vs paths")
ax.legend()
save(fig, "mc_convergence.png")

a_plain = asian_mc(100, 100, 1, 0.05, 0.2, 0, 52, n_paths=200_000, seed=4, control_variate=False)
a_cv = asian_mc(100, 100, 1, 0.05, 0.2, 0, 52, n_paths=200_000, seed=4)
rows.append(("Arithmetic Asian, geometric control variate", f"{a_cv.price:.4f} ± {1.96 * a_cv.stderr:.4f}",
             f"plain MC {a_plain.price:.3f} ± {1.96 * a_plain.stderr:.3f}",
             f"variance cut {a_cv.variance_reduction:,.0f}x"))
dob = down_barrier_call(100, 100, 90, 1, 0.05, 0.25, 0.02)
bb = barrier_mc(100, 100, 90, 1, 0.05, 0.25, 0.02, n_steps=50, n_paths=200_000, seed=2)
nv = barrier_mc(100, 100, 90, 1, 0.05, 0.25, 0.02, n_steps=50, n_paths=200_000, seed=2, brownian_bridge=False)
pde_b = bs_pde(100, 100, 1, 0.05, 0.25, 0.02, lower_barrier=90).price
rows.append(("Down-and-out call: PDE", f"{pde_b:.5f}", f"{dob:.5f}", "Merton / Reiner-Rubinstein closed form"))
rows.append(("Down-and-out call: MC + Brownian bridge (50 steps)", f"{bb.price:.4f} ± {1.96 * bb.stderr:.4f}",
             f"{dob:.5f}", f"naive MC: {nv.price:.3f} (biased)"))

# ============================================================================
section("American options")
LSp = (36.0, 40.0, 1.0, 0.06, 0.2)
pde_a = bs_pde(*LSp, is_call=False, american=True)
lr_a = binomial_price(*LSp, is_call=False, american=True, n_steps=2001)
berm = binomial_price(*LSp, is_call=False, american=True, n_steps=4000, method="crr", exercise_dates=50)
lsm = longstaff_schwartz(*LSp, is_call=False, n_exercise=50, n_paths=200_000, seed=1)
rows.append(("American put S=36,K=40: PDE (CN + penalty)", f"{pde_a.price:.4f}", f"LR tree {lr_a:.4f}", "independent methods"))
rows.append(("Bermudan put, 50 dates: Longstaff-Schwartz", f"{lsm.price:.4f} ± {1.96 * lsm.stderr:.4f}",
             f"4.478 (CRR lattice {berm:.4f})", "Longstaff & Schwartz (2001), Table 1"))

euro_grid = bs_pde(*LSp, is_call=False)
Sg = pde_a.S_grid
m = (Sg > 20) & (Sg < 60)
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.plot(Sg[m], np.maximum(40 - Sg[m], 0), color=MUTED, lw=1.2, ls="--", label="intrinsic value")
ax.plot(Sg[m], euro_grid.V_grid[m], color=SERIES[1], label="European (no early exercise)")
ax.plot(Sg[m], pde_a.V_grid[m], color=SERIES[0], label="American")
ex = Sg[m][np.isclose(pde_a.V_grid[m], np.maximum(40 - Sg[m], 0), atol=1e-6) & (Sg[m] < 40)]
if ex.size:
    ax.axvline(ex.max(), color=INK2, lw=1)
    ax.annotate(f"exercise boundary\nS* ≈ {ex.max():.2f}", (ex.max(), 14), xytext=(6, 0),
                textcoords="offset points", color=INK2, fontsize=9)
ax.set_xlabel("spot S")
ax.set_ylabel("put value (K = 40, T = 1y)")
ax.set_title("American vs European put from the PDE solver")
ax.legend(loc="upper right")
save(fig, "american_put.png")

# ============================================================================
section("GARCH VaR backtest")
gp = GarchParams(0.0002, 3e-6, 0.09, 0.89)
Z99 = 2.3263478740408408
N_TRAIN, N_TEST, WINDOW = 1500, 3000, 250  # Basel-style 250-day historical window


def var_paths(ret):
    """One-day-ahead 99% VaR on the test window: fitted GARCH vs 250d historical simulation."""
    fit = fit_garch(ret[:N_TRAIN])
    p, s2 = fit.params, fit.next_var
    g = np.empty(N_TEST)
    for i, x in enumerate(ret[N_TRAIN:]):
        g[i] = -p.mu + Z99 * np.sqrt(s2)
        s2 = p.omega + p.alpha * (x - p.mu) ** 2 + p.beta * s2
    win = np.lib.stride_tricks.sliding_window_view(ret[N_TRAIN - WINDOW:N_TRAIN + N_TEST - 1], WINDOW)
    h = -np.quantile(win, 0.01, axis=1)
    return g, h


ret, _ = simulate_garch(gp, N_TRAIN + N_TEST, seed=21)
test = ret[N_TRAIN:]
garch_var, hist_var = var_paths(ret)
bt_g, bt_h = backtest_var(test, garch_var, 0.99), backtest_var(test, hist_var, 0.99)


def verdict(bt):
    return "rejected at 5%" if bt.p_cc < 0.05 else "not rejected at 5%"


rows.append(("GARCH(1,1) 99% VaR, one 3000-day test path", f"{bt_g.n_exceptions} breaches, p_cc = {bt_g.p_cc:.3f}",
             f"{bt_g.expected:.0f} expected", verdict(bt_g)))
rows.append(("Historical-sim (250d) 99% VaR, same path", f"{bt_h.n_exceptions} breaches, p_cc = {bt_h.p_cc:.3f}",
             f"{bt_h.expected:.0f} expected", verdict(bt_h)))

# power study: how often does each model fail the conditional-coverage test?
n_hist = 40
rej_g = rej_h = 0
for sd in range(n_hist):
    rr, _ = simulate_garch(gp, N_TRAIN + N_TEST, seed=10_000 + sd)
    g, h = var_paths(rr)
    rej_g += backtest_var(rr[N_TRAIN:], g, 0.99).p_cc < 0.05
    rej_h += backtest_var(rr[N_TRAIN:], h, 0.99).p_cc < 0.05
rows.append((f"Rejection rate over {n_hist} simulated histories (5% test)",
             f"GARCH {rej_g / n_hist:.0%} / historical {rej_h / n_hist:.0%}",
             "5% for a correct model", "Christoffersen conditional coverage"))

fig, ax = plt.subplots(figsize=(9, 4.2))
d = np.arange(test.size)
ax.bar(d, 100 * test, width=1.0, color="#c3c2b7", label="daily return")
ax.plot(d, -100 * hist_var, color=SERIES[1], lw=1.5, label=f"historical-sim VaR ({bt_h.n_exceptions} breaches)")
ax.plot(d, -100 * garch_var, color=SERIES[0], lw=1.5, label=f"GARCH VaR ({bt_g.n_exceptions} breaches)")
br = test < -garch_var
ax.plot(d[br], 100 * test[br], "o", ms=5, color=SERIES[0], mec=SURFACE, mew=1.2)
brh = test < -hist_var
ax.plot(d[brh], 100 * test[brh], "D", ms=5, color=SERIES[1], mec=SURFACE, mew=1.2)
ax.set_xlabel("out-of-sample day")
ax.set_ylabel("return (%)")
ax.set_title(f"99% one-day VaR on a GARCH world ({bt_g.expected:.0f} breaches expected)")
ax.legend(loc="lower left", ncol=3)
save(fig, "var_backtest.png")

# ============================================================================
section("Portfolio construction")
rng = np.random.default_rng(42)
names = ["US Eq", "EU Eq", "EM Eq", "Govt", "Credit", "Gold"]
vols = np.array([0.16, 0.18, 0.22, 0.06, 0.08, 0.15])
corr = np.array([
    [1.0, 0.8, 0.7, -0.2, 0.4, 0.05],
    [0.8, 1.0, 0.7, -0.15, 0.4, 0.05],
    [0.7, 0.7, 1.0, -0.1, 0.45, 0.15],
    [-0.2, -0.15, -0.1, 1.0, 0.5, 0.25],
    [0.4, 0.4, 0.45, 0.5, 1.0, 0.15],
    [0.05, 0.05, 0.15, 0.25, 0.15, 1.0],
])
cov = np.outer(vols, vols) * corr
mu = np.array([0.075, 0.07, 0.085, 0.03, 0.045, 0.05])
rf = 0.02
r_u, v_u, _ = efficient_frontier(mu, cov, 100)
r_l, v_l, _ = efficient_frontier(mu, cov, 40, long_only=True)
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.plot(100 * v_u, 100 * r_u, color=SERIES[0], label="frontier (unconstrained)")
ax.plot(100 * v_l, 100 * r_l, color=SERIES[1], label="frontier (long-only)")
for nm, vv, mm in zip(names, vols, mu, strict=True):
    ax.plot(100 * vv, 100 * mm, "o", ms=6, color=INK2, mec=SURFACE, mew=1.5)
    ax.annotate(nm, (100 * vv, 100 * mm), xytext=(6, -3), textcoords="offset points", fontsize=8, color=INK2)
w_tan = tangency(mu, cov, rf, True)
sr = (w_tan @ mu - rf) / np.sqrt(w_tan @ cov @ w_tan)
xs = np.linspace(0, 0.26, 50)
ax.plot(100 * xs, 100 * (rf + sr * xs), color=MUTED, lw=1.2, ls="--", label=f"capital market line (Sharpe {sr:.2f})")
pts = {"min variance": min_variance(cov, True), "risk parity": risk_parity(cov), "max Sharpe": w_tan}
for (nm, w), c, ms in zip(pts.items(), [SERIES[2], SERIES[4], SERIES[6]], [8, 11, 7], strict=True):
    ax.plot(100 * np.sqrt(w @ cov @ w), 100 * w @ mu, "s", ms=ms, color=c, mec=SURFACE, mew=1.5, label=nm, zorder=5)
ax.set_xlim(0, 26)
ax.set_ylim(1.5, 11.5)
ax.set_xlabel("volatility (%)")
ax.set_ylabel("expected return (%)")
ax.set_title("Efficient frontier and benchmark portfolios")
ax.legend(loc="lower right")
save(fig, "frontier.png")

# ============================================================================
section("Misc. benchmarks")
rows.insert(0, ("Black-Scholes ATM call (S=K=100, r=5%, σ=20%)", f"{bs.price(100, 100, 1, 0.05, 0.2):.6f}",
                "10.450584", "Hull, Options Futures & Other Derivatives"))
_K = np.array([40, 60, 80, 90, 100, 110, 125, 150, 200, 300], float)
_g = np.meshgrid(_K, [0.01, 0.1, 0.5, 1, 3, 5], [0.05, 0.15, 0.3, 0.6, 1.0, 1.5], [True, False], indexing="ij")
_px = bs.price(100, _g[0], _g[1], 0.03, _g[2], 0.01, _g[3])
_vega = bs.greeks(100, _g[0], _g[1], 0.03, _g[2], 0.01, _g[3])["vega"]
_err = np.abs(implied_vol(_px, 100, _g[0], _g[1], 0.03, 0.01, _g[3]) - _g[2])
rows.insert(1, (f"Implied vol round-trip, {_px.size} quotes (σ 5%–150%, T 0.01–5y)",
                f"max error {_err[_vega > 1e-2].max():.1e} (vega > 1e-2)", "0", "safeguarded Newton, vectorised"))
rows.append(("Geometric Asian (52 fixings), closed form", f"{geometric_asian(100, 100, 1, 0.05, 0.2, 0, 52):.6f}",
             "—", "Kemna & Vorst (1990)"))

out = ROOT / "docs" / "RESULTS.md"
with out.open("w") as f:
    f.write("# Benchmark results\n\nGenerated by `python examples/showcase.py` (deterministic seeds).\n\n")
    f.write("| Problem | quantforge | Reference | Source / note |\n|---|---|---|---|\n")
    for row in rows:
        f.write("| " + " | ".join(row) + " |\n")
print(f"\n  wrote {out.relative_to(ROOT)}")
print("\n" + out.read_text())
