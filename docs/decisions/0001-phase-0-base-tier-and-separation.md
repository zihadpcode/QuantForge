# 0001: Phase 0 base, rigor tier, and staying separate from zft-capital

Date: 2026-11-16. Status: approved by the author on 2026-11-17 with the Phase 0 brief.

## Base for the revamp

The worktree branch revamp/phase-0 starts from origin/main at b1e33bc. It is the only branch, local and remote, and the existing checkout was clean. No other line of work was found.

## Rigor tier

Tier A. The library runs on a laptop and holds no personal data, money or credentials. What the tier skips is listed in docs/brief.md. It moves to Tier B if the package is published or a notebook is hosted.

## Build, adopt or adapt

Adapt: keep the from scratch library and use mature libraries as pinned test oracles. Options table in docs/brief.md.

## Merge with zft-capital or stay separate

What was compared (read only): ~/zft-capital at branch phase-1-core-engine.

| | QuantForge | zft-capital |
|---|---|---|
| Kind | Numerical library and research scripts | Event driven lab: order book, matching, order state machine, replay, later paper trading |
| Data model | Float arrays on a fixed clock grid | Integer ticks, shares and cents; event log with a replay hash |
| Dependencies | NumPy, SciPy; Python 3.10 and up | No runtime dependencies; Python 3.15 and up |
| Market | Pricing models; crypto top of book files for the alpha study | U.S. equities and ETFs |
| Stage | Version 1.0.0, feature complete by its README | Phase 1 of its own longer plan |
| Brief | This master prompt | Its own, different master prompt |

Overlap: only the alpha research area. QuantForge has signals, Newey West inference, walk forward fitting, cost aware backtest, Sharpe corrections and a toy market maker. zft-capital has an empty `src/lab/research` package and plans its own simulation and markout analysis. No code is shared or copied between them today.

| Option | Cost | Risk | Reversible | Pick when |
|---|---|---|---|---|
| Stay separate, no link | None | The same statistics may be written twice | Yes | The projects serve different goals |
| Stay separate; zft-capital later depends on QuantForge for evaluation statistics | Small, later | Breaks zft-capital's zero dependency rule and needs QuantForge to support Python 3.15 | Yes | zft-capital reaches its research phase and wants tested statistics |
| Merge into one repository | Days | Two briefs, two data models and two Python floors collide; pricing code has no place in a trading lab | Hard | Never, on current evidence |

Decision proposed: stay separate. Revisit when zft-capital starts its research phase; at that point choose between a dependency on QuantForge and a small port of the few functions needed. The toy market maker in QuantForge stays a teaching model and does not grow toward the zft-capital engine.

What would change this: the author decides QuantForge's alpha subpackage is the only part worth keeping.
