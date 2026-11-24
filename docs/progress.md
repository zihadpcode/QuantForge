# Progress

Read this file first in every session.

Work location: git worktree at ~/projects/revamp/quantforge, branch revamp/phase-0, base origin/main at b1e33bc. Phase 3 changes are uncommitted in the worktree; nothing is pushed. The git history rewrite is not approved and history was not touched.

## Phase 0: Frame

Status: approved by the author on 2026-11-17. The open questions in docs/brief.md were answered with the defaults proposed in the brief, logged in docs/assumptions.md rows 10 to 15 as "default, user to confirm". Decision 0001 (Tier A, stay separate from zft-capital) approved with the brief.

| Step | State |
|---|---|
| Read the code, README, docs and git history | Done |
| Fill section 1 of PROJECT_BRIEF.md from evidence | Done, with unknowns marked |
| Problem statement, success outcome, out of scope | Done, docs/brief.md |
| Prior art and build, adopt or adapt table | Done; maintenance dates confirmed in Phase 1 (docs/requirements.md section 4) |
| Riskiest assumption and cheapest experiment | Done; experiment not run (SciPy not installed locally) |
| Rigor tier | Tier A, approved |
| Audit against sections 6 to 11 and 13 | Done by reading, docs/current-state.md |
| Revamp plan | Done, docs/revamp-plan.md |
| Author approval of the brief | Done, 2026-11-17 |

What was run in Phase 0: ruff 0.17.4 over src, tests and examples (passed); a syntax parse of 29 Python files (passed). The test suite and the example scripts were not run.

## Phase 1: Requirements and risk

Status: approved by the author on 2026-11-19, with every default assumption as written. Defaults in docs/assumptions.md rows 10 to 20 marked accepted 2026-11-19. Decision 0002 accepted (option A).

| Step | File | State |
|---|---|---|
| 0. Record Phase 0 approval; defaults for open questions | docs/progress.md, docs/assumptions.md | Done |
| 1a. User flows, at most seven, by value | docs/requirements.md section 1 | Done, seven flows |
| 1b. Quality requirements as numbers, Tier A scaled | docs/requirements.md section 2 | Done; most numbers are targets, user to confirm |
| 1c. Data classification | docs/requirements.md section 3 | Done |
| 1d. Licenses, data rights, terms of service | docs/requirements.md section 4 | Done, checked 2026-11-17 |
| 2. Threat model, short form | docs/threat-model.md | Done |
| 3. Risk register rebuilt from sections 6 to 11 | docs/risks.md | Done, 32 risks, Phase 0 risks merged |
| 4. Acceptance tests | docs/acceptance-tests.md | Done, 29 tests |
| 5. Phase report and questions | docs/progress.md (below) | Done |
| 6. Decision for a real choice | docs/decisions/0002-binance-data-rights-and-outputs.md | Accepted 2026-11-19, option A |

Exit gate: requirements, risk register and acceptance tests approved. State: met, 2026-11-19.

### Phase 1 report

What was done:
- Seven user flows, led by "reproduce every published number from a fresh clone".
- Quality numbers scaled to Tier A. Response time, availability and concurrency do not apply (no service). They are replaced by runtime budgets: test suite within 120 s, each report script within 10 min, CI within 15 min. Cost ceiling 0 USD. Reproducibility at 100 percent of published numbers.
- Data classification: everything public except raw Binance files and anything derived from them (internal, laptop only), commit author identities (personal, already public), and credentials (secret, never in the repository).
- Licenses and terms for every outside dataset and key dependency, with links and dates. The main finding: Binance Vision files are licensed CC BY NC SA 4.0 under Dataset Terms version 1.0 (2026-08-26). Derived results must carry that license and credit Binance Vision if redistributed. The real data run today writes into the tracked docs/ folder, so a careless commit would breach the terms. Decision 0002 proposes keeping real data outputs local.
- Short threat model with 11 cases; risk register of 32 risks; 29 acceptance tests.

How it was checked:
- Code read at b1e33bc with file and line references; no application code changed.
- Commands run on 2026-11-17: `git count-objects -vH` (1.72 MiB packed); `git log --all --name-only` filtered for data file types (none ever committed); `git ls-files` grep for AI tool names (none); `git log` author and trailer counts (6 commits with a tool author, 10 with a co author trailer); grep for network, shell, pickle and eval use in src, tests and examples (none); `python3 -c "import scipy"` (missing).
- Web checks on 2026-11-17: Binance Vision Dataset Terms PDF (read in full), `binance/binance-public-data` repository, Creative Commons BY NC SA 4.0 deed, Binance prohibited countries page, PyPI pages for each dependency and for the name `quantforge`, Python version status page, GitHub Actions billing page.

What remains uncertain:
- No runtime, memory or reproducibility number has been measured; most quality numbers are targets.
- Whether portfolio use of real data results counts as noncommercial, and whether the author's location affects use of Binance files (assumptions 17 and 20). Not legal advice.
- Whether Binance futures files still use millisecond timestamps (assumption 18).
- The current full Binance Terms of Use page did not load; only the dated prohibited countries list was read.
- CI run history and durations were not checked.
- The history rewrite remains an open decision (R2, A27).

Five questions for the author:
1. If you run the alpha study on a real Binance day and like the result, what must happen before that table or figure can go into this repository, and why can it not simply replace docs/ALPHA_RESULTS.md?
2. Why do response time and availability targets not apply to QuantForge, and which numbers stand in for them?
3. Two README numbers fail acceptance test A2. Which are they, and what would make them pass?
4. The CI matrix tests Python 3.10 to 3.13, yet the latest NumPy and SciPy need 3.12 or newer. What does that mean for the claim that the same commit gives the same digits?
5. The history rewrite is not approved. What does the register say happens to new commits in the meantime, and what must be checked before any rewrite is done?

## Phase 2: Design

Status: approved by the author on 2026-11-22 with decisions 0003 to 0012 as written. Documents only; no application code changed in Phase 2.

| Step | File | State |
|---|---|---|
| 0. Record Phase 1 approval; mark defaults accepted | docs/progress.md, docs/assumptions.md | Done |
| 1a. Major decisions, options tables, keep or change | docs/design.md section 1 | Done, ten decisions |
| 1b. Data model today and its changes; migration approach | docs/design.md section 2 | Done |
| 1c. Interfaces as contracts with types and error cases | docs/design.md section 3 | Done |
| 1d. Response time budget split | docs/design.md section 4 | Does not apply; runtime budgets split instead |
| 1e. Environments and configuration | docs/design.md section 5 | Done |
| 1f. Cost now and at ten times; first limit | docs/design.md section 6 | Done |
| 1g. Architecture diagram | docs/design.md section 7 (Mermaid) | Done |
| 1h. Walking skeleton plan | docs/design.md section 8 | Done |
| 2. One decision note per major decision | docs/decisions/0003 to 0012 | Done, all proposed |
| 3. Risks and revamp plan updated | docs/risks.md, docs/revamp-plan.md | Done: R23 retired pending Phase 3; R33 to R39 added; Phase 3 and 4 slices rewritten |
| 4. Phase report and questions | docs/progress.md (below) | Done |

Exit gate: design approved, every major decision recorded. State: met, 2026-11-22.

### Phase 2 report

What was decided (all proposed, each in its own note):
- 0003 Language: keep Python; change the floor to 3.12; CI 3.12, 3.13, 3.14; 3.12 is the reference.
- 0004 Libraries: keep NumPy and SciPy only at runtime; change extras so matplotlib sits in a new `examples` extra.
- 0005 Environment: change to uv with one committed, hashed `uv.lock` and `uv sync --locked`, locked with a cool off window.
- 0006 Data store: keep plain files, no database; change the output layout so real data runs write only to git ignored local/runs/, raw files to git ignored data/, with exit code 3 for any other target.
- 0007 Reproduction: change to docs/metrics.json plus a hand written docs/claims.toml and one command, `tools/reproduce.py`, with `--check` and a byte for byte `--reference` job.
- 0008 Hosting: no service; keep GitHub and free standard runners; change CI to add macOS, pin actions by commit, read only token.
- 0009 Authentication: does not apply.
- 0010 Background work: does not apply; keep push and pull request triggers, add a manual trigger.
- 0011 Data source: keep simulated data for every published number; keep and harden the Binance loader for local research.
- 0012 Version: change 1.0.0 to 0.9.0 with a changelog; no package index release.
- Cost: 0 USD now and at ten times. First limit: laptop memory on real data runs (loader reads everything into memory), before any GitHub limit.

How it was checked:
- Code read at b1e33bc: pyproject.toml, tests.yml, .gitignore, src/quantforge/alpha/data.py, the output paths in both example scripts, `taker_backtest` in evaluation.py.
- Commands run on 2026-11-19: `uv --version` (0.13.7, Homebrew); `uv python list --only-installed` (3.12.1 and others present); a look in the uv cache (no SciPy wheel cached, so an offline install is not possible); `uv export --help` and `uv lock --help` (hash and exclude newer flags exist); PyPI JSON for numpy, scipy, matplotlib, scikit-learn, statsmodels, pytest and ruff.
- Pages read on 2026-11-19: https://devguide.python.org/versions/ , https://docs.github.com/en/billing/concepts/product-billing/github-actions , https://docs.astral.sh/uv/concepts/projects/layout/ , https://docs.astral.sh/uv/concepts/projects/sync/ , https://docs.astral.sh/uv/concepts/projects/export/ .
- Nothing was installed, built, run against the library, committed or pushed.

What remains uncertain:
- Every runtime budget split is a target; nothing has been timed (assumption 25).
- Whether macOS and Linux print the same digits (assumption 24), which sets the tolerances.
- Whether the committed reports still match the code. This is the riskiest assumption and needs the Phase 3 install (assumption 27, R39).
- The uv documentation pages read did not state the hash behavior; it is inferred from the CLI help and a local lockfile (assumption 22).
- Wheel availability for matplotlib, scikit-learn and statsmodels on 3.13 and 3.14 (assumption 23). GitHub concurrent job limits and the current runner image list were not checked.
- The history rewrite remains an open decision (R2); nothing here depends on it.

Five questions for the author:
1. Why does the design require byte for byte equal reports in only one CI job, and compare numbers within a tolerance everywhere else?
2. You run the alpha study on a real Binance day and pass `--out docs`. What happens, and which decisions make it happen?
3. Why move the Python floor to 3.12 instead of keeping 3.10, and what in pyproject.toml and CI changes because of it?
4. A new number is added to the README table but nobody adds a line to docs/claims.toml. What does `tools/reproduce.py --check` do, and which risk does that answer?
5. Why does a `latency_steps` default of 0 leave the published numbers unchanged, and why does the real data path still report a latency of 1?

## Phase 3: Scaffold and walking skeleton

Status: in progress, started 2026-11-22 after the author approved Phase 2. Work done without network: no install, no lock, no push, no commit. SciPy is not installed on the Mac, so the existing suite cannot run here; new tests use only the standard library.

### Environment used

| Tool | Version | Source |
|---|---|---|
| Python | 3.12.1 | /usr/local/bin/python3.12 (python.org build); has NumPy 2.3.5 and matplotlib 3.10.8, no SciPy |
| pytest | 9.2.0, with pluggy 1.7.0, iniconfig 2.3.1, packaging, pygments | already in the uv cache (~/.cache/uv/archive-v0), put on PYTHONPATH; nothing installed |
| ruff | 0.17.4 | already in the uv cache, the binary Phase 0 used |
| uv | 0.13.7 | Homebrew |
| mypy | cached, but does not start: `ModuleNotFoundError: No module named 'librt.internal'` | not usable; type check stays in slice 4.7 |

`PYTEST` below means `PYTHONPATH="src:<cached pytest, pluggy, iniconfig, packaging, pygments dirs>" python3.12 -m pytest -p no:cacheprovider`. `RUFF` means `~/.cache/uv/archive-v0/kQwbW6plDZNw5lYz/ruff-0.17.4.data/scripts/ruff`.

### Slices

| Slice | State | What was done | Check run and result |
|---|---|---|---|
| 3.1 Python floor and lock (0003, 0004, 0005) | Partly done. Blocked: needs the author's yes for a network install from PyPI to run `uv lock --exclude-newer <about 14 days back>` and `uv sync --locked --extra dev` | pyproject.toml: `requires-python = ">=3.12"`, ruff `target-version = "py312"`, new `examples = ["matplotlib>=3.7"]` extra, `dev` now holds `quantforge[examples]` instead of matplotlib. README badge says 3.12+. Lock command written in docs/runbook.md section 1 | `RUFF check --no-cache src tests examples`: "All checks passed!" (no `UP` findings at py312). `uv lock --offline --dry-run`: "Because numpy was not found in the cache ... unsatisfiable", which confirms the lock needs the network. A4 and A16 not run |
| 3.2 First reproduction run by hand | Blocked: needs SciPy, so needs slice 3.1's install yes. Not started | Nothing; this is the riskiest assumption and is still untested | Not run |
| 3.3 Ignore rules and version (0006, 0012) | Done | .gitignore adds `data/`, `local/`, `*.zip`, `*.csv` with a comment on why. Version 0.9.0 in pyproject.toml and src/quantforge/__init__.py. New CHANGELOG.md | `git check-ignore data/x.zip local/runs/a/report.md` printed both paths, exit 0 (A13). `git ls-files` shows no tracked .csv, .zip, data/ or local/ file. tests/test_project_config.py checks the rules and the version |
| 3.4 CI rework (0008, 0009, 0010) | Partly done. Blocked: (a) pin each action by commit needs a read only lookup of each tag's commit (network); (b) setup-uv plus `uv sync --locked` needs uv.lock (slice 3.1); (c) secret scan and dependency audit need a tool chosen by options table and approved; (d) a green run needs a push | tests.yml: matrix ubuntu-24.04 with 3.12, 3.13, 3.14 plus macos-15 with 3.12; `fail-fast: false`; 15 minute timeouts; `permissions: contents: read`; `workflow_dispatch`; `persist-credentials: false` on checkout; ruff now also checks tools/; new reproduce job. Installs still use pip so CI keeps working until the lock exists. Target steps in docs/runbook.md section 5 | tests/test_project_config.py WorkflowTest (5 tests) passes. YAML not run by GitHub; runner image names not checked against the current image list (assumption 28) |
| 3.5 Walking skeleton (design section 8) | Done in code; not run end to end (needs SciPy). Exit gate open | examples/report_io.py (standard library: output guard, RUN_ID, metrics writer). showcase.py: body moved into `main(argv) -> int` unchanged, `--out DIR`, writes `bs.atm_call` into DIR/metrics.json; an unused `rng` line removed. alpha_research.py: `main(argv) -> int`, `--out`, real data default local/runs/RUN_ID, exit 3 outside local/ before any read or write. docs/metrics.json, docs/claims.toml (one claim), tools/reproduce.py with `--check` and `--reference`, exit codes 0 to 4. CI reproduce job runs `--check` | `PYTEST tests/test_project_config.py tests/test_report_io.py tests/test_reproduce.py tests/test_alpha_outputs.py -rs`: "37 passed, 2 skipped, 7 subtests passed in 0.09s" (the 2 skips need SciPy). Same files with `python3.12 -m unittest ...`: "Ran 37 tests ... OK (skipped=2)". Three timed runs: 0.27 s, 0.26 s, 0.27 s. A one off smoke script (scratchpad, quantforge modules stubbed) called alpha_research.main: `--out docs` returned 3 with the error message; the default went to local/runs/BTCUSDT_2024-03-01_20261122T1000Z and reached the loader. `RUFF check --no-cache src tests examples tools`: "All checks passed!" |

Left for slice 4.1, as planned: the checker does not yet list README numbers that no claim covers, and does not yet count collected tests. A small difference from docs/design.md section 2: metrics.json records the generator on each metric rather than per section, so one script can replace its own entries without touching the other's.

docs/metrics.json was written by `report_io.write_metrics` with the Black Scholes value computed by `math.erfc` (10.450583572185565), not by showcase.py, because SciPy is missing. The first `python tools/reproduce.py` with SciPy must regenerate it; the claim's tolerance (5e-7) and the printed digit check decide if the two agree (assumption 29).

### Test suite before and after

| When | Command | Result |
|---|---|---|
| Before any change | `PYTEST` | "6 errors in 0.26s": every existing test file fails to import (`ModuleNotFoundError: No module named 'scipy'`); 0 tests ran |
| After | `PYTEST` | "6 errors in 0.15s": the same 6 files, same cause; the run stops at collection |
| After | `PYTEST --continue-on-collection-errors` | "37 passed, 2 skipped, 6 errors": all new tests pass; the 6 old files still cannot import |
| Before and after | `RUFF check --no-cache src tests examples` | "All checks passed!" |

No existing test could run before or after, so "no test newly fails" is shown only for collection. The existing 80 test functions must be run once SciPy is installed.

### Suggested commit messages (human author, no tool trailers)

- 3.1: `build: require Python 3.12 and move matplotlib to an examples extra`
- 3.3: `chore: ignore raw data and local runs; reset version to 0.9.0 with a changelog`
- 3.4: `ci: test 3.12 to 3.14 and macOS with a read only token and manual trigger`
- 3.5: `feat: add metrics.json, claims.toml and tools/reproduce.py; guard real data output`
- records: `docs: phase 3 progress, runbook, risks and assumptions`

### Exit gate

Skeleton runs locally and on the target, checks pass, rollback shown. State: open. What remains:

1. The author's yes for the network install; then `uv lock --exclude-newer ...`, `uv sync --locked --extra dev`, `uv run pytest` (the 80 existing tests plus the new ones) and slice 3.2.
2. With SciPy present: `python tools/reproduce.py` once to regenerate docs/metrics.json from showcase.py, then `--check` passes; `git diff docs/RESULTS.md` shows whether the refactored showcase.py still writes the same bytes, apart from the wall time in the calibration row.
3. A push (the author's yes) so CI runs; green as is, and red on a branch with one edited digit (A3).
4. Commit ids for the action pins; then the uv based CI steps.
5. Rollback is "revert the commit" (docs/runbook.md section 7); not rehearsed, since nothing is committed.

## Next action

The author answers the Phase 3 questions and says yes or no to: the PyPI install for uv.lock; a read only lookup of action commits; a push of the branch. The coordinating session commits the slices above.

## Phases 4 to 8

Not started. Phase 4 slices are in docs/revamp-plan.md.
