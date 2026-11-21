# QuantForge: Phase 0 brief

Date: 2026-11-16. Status: approved by the author on 2026-11-17. Open questions answered by defaults in docs/assumptions.md rows 10 to 15. Base: origin/main at b1e33bc.

## Problem statement

Who: one student author who wants reference quant code that can be defended line by line, and readers of the public repository.

Today: the library exists (about 2,700 lines of source, 80 test functions, two report scripts). It makes many numeric claims in README.md. A reader has to trust them, because nothing checks that the README still matches the code, the install is not pinned, and the test suite cannot run on the author's own machine (SciPy is not installed there).

What changes: every number in the README comes from one command on a fresh clone, a check in continuous integration fails when a number drifts, the alpha study states its execution assumptions, and the git history names only human authors.

## Success outcome

One measurable outcome: on a fresh clone, one documented command regenerates 100 percent of the numeric claims in README.md, docs/RESULTS.md and docs/ALPHA_RESULTS.md, and a continuous integration job fails if any differs beyond a stated tolerance.

Check date: 2026-12-14 (proposed, four weeks out; the author confirms).

## Out of scope

- Live trading, order routing, broker links, real money.
- Any hosted service or web interface.
- Portfolio backtests over real stock universes. This is where survivorship bias would enter, and the library has no universe data today.
- New pricing models, until the reproducibility outcome is met.
- Merging with zft-capital (see docs/decisions/0001).
- Speed work without a profile.

## Prior art

Searched 2026-11-16. Maintenance dates were not confirmed on each project's own page; do that in Phase 1.

| Option | What it means | Cost | Risk | Reversible | Pick when |
|---|---|---|---|---|---|
| Adopt QuantLib (Python bindings) or FinancePy | Stop building pricing code, use a mature library | Low build cost, high learning of a large API | The author learns less; neither covers the alpha statistics | Yes | The goal is to price real trades |
| Adopt statsmodels, scikit-learn, arch | Use them for Newey West, Ledoit Wolf, GARCH | Adds runtime dependencies | Breaks the NumPy and SciPy only rule | Yes | Those parts stop being a learning goal |
| Adapt: keep QuantForge, use the mature libraries as test oracles | Current approach, extended | Small: dev only dependencies | Oracles can drift between versions; pin them | Yes | The goal is understanding plus evidence |
| Build more from scratch with no oracles | Self checks only | Lowest dependency count | Errors shared by code and test go unseen | Yes | Never recommended here |

Recommendation: adapt. Keep the from scratch library, and widen the cross checks against pinned reference libraries in the dev group (statsmodels and scikit-learn are already used this way in tests/test_alpha.py line 91 and the Ledoit Wolf test). Not yet: a rewrite on top of QuantLib, because the stated value of the project is code the author can explain.

Sources: https://github.com/domokane/FinancePy , https://wilsonfreitas.github.io/awesome-quant/ , https://pypi.org/project/optpricing/ , https://pypi.org/project/pyfeng/

## Riskiest assumption

Assumption: the published numbers are still what the code produces. The README was edited by hand in several commits (for example 1cc9f13 "README: restore test count") and two headline numbers, 34 of 40 and 4 of 40 at README.md lines 81 and 82, are printed by no script. The test only asserts bounds (tests/test_alpha.py lines 128 and 129).

Cheapest experiment: in a clean environment with pinned versions, run `pytest`, `python examples/showcase.py` and `python examples/alpha_research.py`, then diff the regenerated docs/RESULTS.md and docs/ALPHA_RESULTS.md against the committed files and compare each README number by hand. One hour. Any difference disproves the assumption. This was not possible in Phase 0 because SciPy is not installed locally and network installs were not allowed.

## Rigor tier

Tier A: runs on the author's laptop, holds no personal data, money or credentials.

Skipped, with reason:
- Hosting, deployment, rollback, monitoring, cost caps (sections 8 and 10, Phase 6): there is no service.
- Threat model beyond supply chain and untrusted input files: no accounts, no network entry points.
- Backup and restore rehearsal: all outputs are regenerated from seeds; git is the only store.
- Load tests: not a request path. A runtime budget for the test suite replaces them.

Kept at full rigor: correctness, tests, reproducibility, dependency pinning and audit, secret scan of history.

The tier moves to B if the package is published to a package index or the notebook is hosted.

## Open questions

| Question | Owner | Resolve by |
|---|---|---|
| Is the audience recruiters and interviewers, other students, or the author only? | Author | 2026-11-23 |
| Approve a history rewrite to remove the tool author and trailers? (needs a force push) | Author | 2026-11-23 |
| Will the package be published to a package index? | Author | 2026-11-30 |
| Hours per week and deadline for this project | Author | 2026-11-23 |
| Is version 1.0.0 intended as a stable public API promise? | Author | 2026-11-30 |
| Has the pipeline ever been run on real Binance files, and are those results meant to be published? | Author | 2026-11-30 |
