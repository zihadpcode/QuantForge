# 0003: Language and supported Python versions

Date: 2026-11-19. Status: accepted 2026-11-22 (proposed in Phase 2). Options table: docs/design.md section 1.1.

## Decision

Keep Python. Change `requires-python` from `>=3.10` to `>=3.12`. CI tests 3.12, 3.13 and 3.14. Python 3.12 is the reference version for published digits. 3.15 joins the matrix when every locked dev package ships a wheel for it.

## Why change

Phase 1 risks R11 and R23 and acceptance test A25 fail today. Python 3.10 reached end of life on 2026-10-01, and the latest NumPy (2.5.5) and SciPy (1.18.1) require 3.12 or newer, so the 3.10 and 3.11 jobs test older libraries than the ones that would make the published numbers.

## Evidence

- https://devguide.python.org/versions/ checked 2026-11-19.
- PyPI JSON for numpy, scipy, matplotlib, scikit-learn, statsmodels, pytest and ruff, checked 2026-11-19 (versions and floors in docs/design.md section 1.1).
- Python 3.12.1 is installed on the author's Mac (`uv python list --only-installed`, 2026-11-19).

## Consequences

- Users on 3.10 or 3.11 lose support. None is known.
- `tool.ruff.target-version` moves to `py312`; ruff `UP` rules may flag small syntax updates, fixed in the Phase 3 slice that makes the change.

## What would change this

An outside user who needs 3.11, or a dependency that drops 3.12 earlier than its end of life in 2028-10.
