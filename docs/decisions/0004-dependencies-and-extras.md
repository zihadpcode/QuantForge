# 0004: Libraries and dependency groups

Date: 2026-11-19. Status: accepted 2026-11-22 (proposed in Phase 2). Options table: docs/design.md section 1.2.

## Decision

Keep NumPy and SciPy as the only runtime dependencies. Change the extras: a new `examples` extra holds matplotlib; `dev` holds pytest, ruff, scikit-learn and statsmodels and includes `examples`. No QuantLib or FinancePy oracle now. The lockfile (decision 0005) fixes every version; the lower bounds in pyproject.toml stay as compatibility floors.

## Why

Keep: nothing in Phase 1 shows the NumPy and SciPy rule failing (assumption 8). Change: the example scripts need matplotlib but have no documented install of their own (docs/current-state.md, library addendum).

## What would change this

A pricing claim with no independent check (then QuantLib, BSD 3 Clause, as a dev oracle by a new decision). FinancePy stays out unless a decision accepts a GPL tool in the test chain (R8).
