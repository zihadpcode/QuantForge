# Acceptance tests

Phase 1. Date: 2026-11-17. Plain language. Each test names how it is checked and its status today: passes today (with evidence), fails today, or not yet testable. "Not yet testable" mostly means the suite cannot run on the author's Mac until a pinned environment exists (SciPy missing; `python3 -c "import scipy"` gave ModuleNotFoundError on 2026-11-17).

## Per user flow

| # | Flow | Test | How it is checked | Status today |
|---|---|---|---|---|
| A1 | F1 | On a fresh clone, one documented command regenerates docs/RESULTS.md, docs/ALPHA_RESULTS.md and all figures | Run it in a new folder; `git status` shows no changed report files | Not yet testable: no pinned environment, and no single command exists (two scripts) |
| A2 | F1 | Every numeric claim in README.md appears in a generated file | A script lists README numbers and finds each in generated output | Fails today: "34 / 40" and "4 / 40" (README lines 81, 82) are printed by no script (grep of examples and src, 2026-11-17) |
| A3 | F1, F7 | CI fails if a committed report number is edited by hand | Edit one digit in docs/RESULTS.md on a branch; CI goes red | Fails today: CI runs only ruff and pytest (tests.yml lines 19, 20) |
| A4 | F2 | The full suite passes on the author's Mac from documented commands and prints the test count | `pytest` in the pinned environment | Not yet testable: SciPy missing locally |
| A5 | F2 | Lint passes | `ruff check src tests examples` | Passes today: ruff 0.17.4 reported all checks passed on 2026-11-16 (docs/current-state.md "What was run") |
| A6 | F3 | Each public pricing and risk function rejects invalid input (negative volatility, empty array, maturity of zero where undefined) with a clear error | One test per public function | Fails today: for example historical VaR accepts an empty array (docs/current-state.md section 9) |
| A7 | F4 | `python examples/alpha_research.py` with no arguments finishes and reproduces the committed docs/ALPHA_RESULTS.md exactly | Run, then `git diff --exit-code docs/ALPHA_RESULTS.md` | Not yet testable: SciPy missing locally |
| A8 | F5 | The notebook runs top to bottom without error in the pinned environment | `jupyter nbconvert --execute` or equivalent, in CI | Not yet testable: no environment; not in CI today |
| A9 | F6 | A real data run writes nothing under docs/ and nothing git tracks | Run with a small synthetic file shaped like Binance data; `git status --porcelain` is empty | Fails today: the script writes docs/ALPHA_RESULTS.md (examples/alpha_research.py line 241) and docs/figures (line 29) for any source |
| A10 | F6 | A real data report states latency, timestamp field and timestamp unit | Read the report header; a test checks the fields exist | Fails today: no latency parameter (evaluation.py line 221); grid uses `transaction_time` silently (data.py line 125) |
| A11 | F6 | The loader rejects a file whose timestamps are in microseconds, or converts them by an explicit choice | Unit test with a microsecond file | Fails today: units are assumed to be milliseconds (data.py lines 7 to 10) |
| A12 | F6 | A research record (question, symbol, dates, how chosen, file names, checksums, download date) exists before any real data result is kept | File present in docs before the run | Not yet testable: no real data study planned |
| A13 | F6 | Git refuses to track raw data files | `git check-ignore` on a sample `.zip` and `.csv` in the data folder | Fails today: .gitignore has no data rules (.gitignore lines 1 to 7). No data file is tracked or in history (checked 2026-11-17), so there is no breach today |
| A14 | F7 | A pull request with a failing test or a drifted number cannot show a green CI | Open a test branch with one broken test and one edited number | Partly: a failing test turns CI red (tests.yml line 20, not observed today); a drifted number does not (see A3) |

## Per quality number

| # | Quality | Test | How it is checked | Status today |
|---|---|---|---|---|
| A15 | Reproducibility 100 percent | A1, A2 and A3 all pass | As above | Fails today (A2, A3) |
| A16 | Test suite within 120 s | Worst of 3 timed runs of `pytest` on the author's Mac | `time pytest`, three times, recorded in docs/progress.md | Not yet testable |
| A17 | Report scripts within 10 min each | Time each script once on the author's Mac | `time python examples/showcase.py`, same for alpha_research.py | Not yet testable |
| A18 | CI job within 15 min | Read job durations on the last 5 main runs | GitHub Actions run page | Not yet testable here: CI history not checked in Phase 1 (no network use beyond search) |
| A19 | Repository under 10 MB packed | `git count-objects -vH` | Read size-pack | Passes today: 1.72 MiB on 2026-11-17 |
| A20 | Real data run under 4 GB peak memory; files above the cap refused | `/usr/bin/time -l` on one real day; unit test with an oversized file | Measure, then test | Not yet testable for memory (no real file); fails today for the cap (no cap at data.py line 64) |
| A21 | Cost 0 USD a month | No paid service in the repository or the docs; CI uses standard runners in a public repository | Read tests.yml and the docs | Passes today: tests.yml uses `ubuntu-latest` only (line 9); standard runners are free for public repositories (GitHub docs, checked 2026-11-17) |
| A22 | Environment rebuilt from a fresh clone within 30 min | Time the setup on a fresh clone | Stopwatch, recorded in docs/progress.md | Not yet testable: no pinned setup |
| A23 | Acceptable data loss: reports regenerate exactly | Same as A1 and A7 | | Not yet testable |
| A24 | Supported platforms: macOS and Ubuntu | CI matrix includes macOS and Ubuntu, both green | Read tests.yml and a run | Fails today: Ubuntu only (tests.yml line 9) |
| A25 | Python versions: every declared version is supported upstream and tested | `requires-python` matches the CI matrix and excludes end of life versions | Read pyproject.toml line 10 and tests.yml line 12 | Fails today: 3.10 is declared and tested but reached end of life on 2026-10-01 |

## Rules and data rights

| # | Test | How it is checked | Status today |
|---|---|---|---|
| A26 | No tracked file names an AI tool as author or contributor | `git ls-files` piped to a case insensitive grep for tool names | Passes today: no tracked file matched (2026-11-17). Untracked Phase 0 docs quote the trailer as evidence only |
| A27 | No commit names an AI tool as author or carries an AI co author trailer | `git log` format check on author, committer and message trailers | Fails today: 10 of 10 commits carry the trailer; 6 list the tool as author (2026-11-17). Fixing it needs an approved history rewrite; not approved |
| A28 | Any published result derived from Binance data sits in a folder marked CC BY NC SA 4.0 with attribution to Binance Vision | Read the folder's license notice | Passes today vacuously: no such result is published (assumption 6). Becomes a real check with the first real data publication |
| A29 | No network calls, shell commands, pickle or eval in src, tests or examples | grep | Passes today: none found (2026-11-17) |
