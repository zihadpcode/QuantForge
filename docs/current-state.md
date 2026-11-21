# Current state audit

Date: 2026-11-16. Code audited: origin/main at b1e33bc. Bounded by what was read and run; see "What was run".

## What exists

- Package `quantforge` under src: 14 pricing, risk and portfolio modules plus the `alpha` subpackage (signals, evaluation, market making, simulator, Binance file loader). About 2,700 lines.
- Tests: 80 test functions in 6 files, 9 parametrize uses. The README says 96 tests.
- Two report scripts: examples/showcase.py and examples/alpha_research.py. They write docs/RESULTS.md, docs/ALPHA_RESULTS.md and docs/figures.
- One notebook, notebooks/quickstart.ipynb, 35 cells, 17 with stored outputs.
- Continuous integration: ruff then pytest on Python 3.10 to 3.13 (.github/workflows/tests.yml).
- README, LICENSE (MIT), docs/ALPHA.md guide.

## What was run

| Command | Result |
|---|---|
| `~/zft-capital/.venv/bin/ruff check --no-cache src tests examples` (ruff 0.17.4, borrowed from a sister project) | All checks passed |
| Python `ast.parse` over 29 source, test and example files | 29 parsed, no syntax errors |
| `pytest` | Not run. SciPy is not installed in any local interpreter and network installs were out of bounds |
| `python examples/showcase.py`, `python examples/alpha_research.py` | Not run, same reason |

So no test result and no README number was confirmed in Phase 0. The claims below about numbers are from reading code only.

## Lookahead bias

Checked by reading; found no lookahead in these places:
- Signals use trailing windows and a causal EWMA (signals.py lines 54 to 90). A test perturbs the future and compares the past (tests/test_alpha.py lines 40 to 62).
- Walk forward splits drop training rows whose label reaches the test block, and the ridge refuses an embargo shorter than the horizon (evaluation.py lines 128 to 157). Features are scaled with training statistics only.
- The event sampler uses the last quote at or before each grid time and buckets trades into the interval ending at the grid time (data.py lines 96 to 108).
- The VaR backtest fits GARCH on the training span only, and the historical window ends the day before each forecast (examples/showcase.py lines 224 to 234).

Open lookahead items:
1. Zero latency fills. `taker_backtest` reads the forecast at step t and trades at the quote of the same step t (evaluation.py line 221 with lines 219 and 223). The forecast already uses the book and trades of step t. On 100 ms real data this fill is not reachable. No latency parameter exists. On simulated data it flatters the result; the report still shows the strategy losing after fees.
2. Exchange time, not receipt time. `load_binance` grids on `transaction_time` (data.py line 125). The file also carries `event_time`. A remote trader sees data later than either stamp, so real data results would be optimistic.
3. Selection on the test set. Thresholds are compared on the same out of sample forecasts and the best is reported (examples/alpha_research.py lines 148 to 154). The Deflated Sharpe step is the stated correction (lines 179 to 200), but its trial variance is taken from trials that include true alphas, which is not the null setting the formula assumes.
4. Full sample decile edges in `quantile_returns` (evaluation.py line 118). Descriptive only, but it is not a tradable ranking.
5. The ridge penalty is fixed at 1.0 (evaluation.py line 142). Not a leak today. It becomes one if anyone tunes it on the test folds; no nested split exists.

## Survivorship bias

Not present in the published results, because they use one simulated instrument. It is also not guarded: the loader takes whatever files the user picks (data.py line 117), with no record of symbol, date or how the day was chosen. A study on a hand picked liquid symbol and day is a selection effect. The docs do not say this.

## Are the README performance claims reproducible?

| Claim | Location | Status |
|---|---|---|
| Validation table | README.md lines 34 to 50 | Script exists (examples/showcase.py). Not run here. No CI check that README matches docs/RESULTS.md |
| "34 / 40" and "4 / 40" false positive counts | README.md lines 81 and 82, docs/ALPHA.md line 341 | Not reproducible from any documented command. The test asserts only `fp_nw <= 6` and `fp_naive >= 25` (tests/test_alpha.py lines 128, 129) |
| Ridge R squared 0.103, IC 0.32, break even 1.0 bp, Sharpe figures | README.md lines 83 to 86 | Script exists and is seeded (examples/alpha_research.py). Matches the committed docs/ALPHA_RESULTS.md by reading. Not run here |
| "IV RMSE 1.9e-08 in 0.9 s" | README.md line 44 | The 0.9 s is wall time on an unnamed machine (examples/showcase.py lines 86 to 88). Not reproducible as stated |
| "96 tests, about 45 s" | README.md lines 28, 172, 235 | Hand typed; commit 1cc9f13 exists only to fix this count. Machine not named |
| Sharpe 7.13 for the alpha market maker | README.md line 86 | Reproducible by seed, but it assumes the dealer sees the true drift exactly. The README footnote says so. It is a per session ratio on a toy model, not a trading result |

Versions are not pinned (pyproject.toml line 12 and line 18 use lower bounds, no lockfile), so the same commit can give different digits with a different NumPy or SciPy.

## Against master prompt sections

Section 6, security (Tier A, light):
- No secrets found in the tree by grep; history was not scanned with a secret scanner.
- Supply chain: no lockfile, no hashes, no dependency audit, CI actions pinned by tag not by commit (tests.yml lines 14, 15).
- Untrusted input: `read_binance_csv` reads the first member of any zip fully into memory with no size limit (data.py line 64) and loads every row into Python lists (line 67). A large or hostile file exhausts memory.
- No network, shell, eval or pickle use found in src, tests or examples (grep).

Section 7, performance: no budget, no benchmark. The "45 s" suite time is the only number and it is not measured in CI.

Section 9, reliability and data:
- `order_flow_imbalance` turns every NaN into zero before summing (signals.py line 127), so missing data becomes a silent "no flow" reading.
- `ewma` propagates one NaN to every later value (signals.py line 72), which blanks normalized OFI for the rest of the series.
- `zscore_trailing` computes variance as mean of squares minus square of mean (signals.py line 88), which loses precision on series with a large mean.
- No schema or sanity checks at ingestion: crossed quotes, zero sizes and non monotone times pass through (data.py lines 87 to 113).
- Most public functions do not validate inputs (for example `historical_var_es`, risk.py, accepts an empty array).

Section 11, process: stale documentation risk is live (hand typed README numbers). Overconfident claims: the README line "every model checked" is bounded only by tests that were not run here.

Section 13, definition of done:
- Standard files missing: PROJECT_BRIEF.md (added in this phase), example environment file (not needed, record that), docs/brief.md, progress, assumptions, risks, decisions (added in this phase), runbook and architecture diagram (missing).
- "Fresh clone runs from the README": unproven. The README install line (line 171) pulls unpinned packages.

Addendum, library:
- Semantic versioning: version 1.0.0 with no git tag, no changelog, no release.
- Public surface: `quantforge/__init__.py` lines 22 to 56 import 14 modules but not `alpha`, while the docstring lists it (line 19). No `py.typed`, no type check in CI.
- Examples do not run in CI (tests.yml has only ruff and pytest). matplotlib, needed by both examples, sits only in the dev extra.
- Supported platforms: CI covers Ubuntu only; macOS, the author's platform, is untested.

Addendum, research:
- The question was not written before the data. docs/ALPHA.md is a guide written after.
- Figures: scripts exist for all of them. Good.
- Data sources and dates: no record for real data runs.
- Uncertainty: Monte Carlo rows carry confidence widths. The alpha table gives point values with no intervals across seeds (one seed each).
- Negative results: kept. The report says the taker strategy does not survive fees and that GARCH is rejected 10 percent of the time.

Other defects:
- tests/test_alpha.py line 239 accepts a 4 percent gap to the Avellaneda and Stoikov paper value with the comment "we get ~64.8". The replication claim is looser than it reads.
- Git authorship: see below.

## Git authorship

All 10 commits on main carry the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and a `Claude-Session:` link line. Six commits also have author and committer set to `Claude <noreply@anthropic.com>`: b1e33bc, f92e861, e978007, d783e93, 1cc9f13, 8cc3b83. The four older commits (eb5386e, 81e0144, 8a851a7, a0512c8) have the human author but still carry both trailers. No AI tool name was found in tracked file contents (grep).

Proposed fix, not performed: rewrite the 10 commits so author and committer are the human identity and both trailer lines are removed, then force push main. For example `git filter-repo` with a mailmap plus a message callback, on a fresh clone, after saving a backup bundle. This is a history rewrite and a force push, so it needs an explicit yes. Side effects: every commit id changes, the CI badge history resets, and any clone or fork must re-sync. A lighter option that leaves history alone is recorded in docs/revamp-plan.md.

## Largest gaps, ranked by damage times likelihood

| Rank | Gap | Damage | Likelihood |
|---|---|---|---|
| 1 | README numbers are not tied to code; two have no generating script; nothing ran locally | High for a project whose point is evidence | High |
| 2 | AI tool listed as author or co-author on every commit | High against the author's own rule | Certain |
| 3 | No pinned environment; tests cannot run on the author's machine | High | Certain |
| 4 | Zero latency and exchange time assumptions in the real data path, undocumented | High once real data is used | Medium |
| 5 | Silent NaN handling and no ingestion checks | Medium | Medium on real data |
| 6 | Version 1.0.0 with no tag, no changelog, `alpha` missing from the top level, examples not in CI | Medium | High |
