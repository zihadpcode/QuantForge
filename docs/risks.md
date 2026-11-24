# Risk register

Started 2026-11-16 in Phase 0. Rebuilt 2026-11-17 in Phase 1 from master prompt sections 6 to 11, merged with the Phase 0 risks and deduplicated. Updated 2026-11-19 in Phase 2: see "Phase 2 changes" at the end; rows marked (P2) were edited. Likelihood and damage are low, medium or high (certain means it is already true). Phase is the phase that handles the mitigation. "P0 #n" marks the Phase 0 risk number it replaces.

Ranked by damage times likelihood within each section.

## Data rights and terms (Phase 1 focus)

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R1 (P2) | Results derived from Binance Vision files are committed into the MIT repository without CC BY NC SA 4.0 notice and attribution, breaching Dataset Terms 4.5. The real data run writes over the tracked report and figures (examples/alpha_research.py lines 29 and 241) | Medium | High | Decision 0002 (accepted, option A) and 0006: real data outputs go to local/runs/, the script exits 3 for any other folder; ignore rules for data/, local/, *.zip, *.csv; a test for the guard. Publishing needs a new decision (option B) | 3, 4 |
| R2 | Git history names an AI tool as author on 6 commits and as co author on all 10, against the working agreement. Rewrite is not approved (P0 #2) | Certain | High | Open decision for the author. Options in docs/revamp-plan.md. Until decided: no rewrite, no force push; new commits use the human identity with no AI trailers; check forks before any rewrite (assumption 9) | Open; 3 if approved |
| R3 | Raw Binance zips get committed or hosted (terms 4.3, 4.5) | Low | High | `.gitignore` rules for `*.zip`, `*.csv` and a data folder; acceptance test A13 | 3 |
| R4 | Using the data counts as commercial (for example a paid project, or a job application read as commercial advantage) | Low | Medium | Keep real data use to personal research; author confirms assumption 17; ask Binance for a written license before any commercial use (terms 3.4) | 1, 7 |
| R5 | The author's location is on Binance's prohibited list and downloading is outside the terms | Unknown | Medium | Author confirms assumption 20 before downloading; simulated data stays the default path | 1 |
| R6 | Binance withdraws a dataset or changes its format (terms 5.3; SPOT already moved to microsecond timestamps from 2025-01-01), so a real data study cannot be rerun or is misread | Medium | Medium | Research record keeps file names, download dates and checksums; loader checks timestamp units (assumption 18) | 4, 5 |
| R7 | The README or docs imply Binance endorsement (terms 8.2) | Low | Low | Name Binance only to describe file formats; no logos | 7 |
| R8 (P2) | GPL code (FinancePy) copied into the MIT repository | Low | Medium | Decision 0004: no FinancePy; a GPL dev tool needs its own decision; never copy | 2 (done), all |

## Correctness and evidence (sections 7, 9 and the research addendum)

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R9 (P2) | README numbers drift from what the code produces; two (README lines 81, 82) have no generating script (P0 #1) | High | High | Decision 0007: metrics.json, claims.toml and `tools/reproduce.py --check` in a CI reference job; acceptance tests A1 to A3 | 3, 4, 7 |
| R10 | Tests cannot run on the author's machine (SciPy missing, checked 2026-11-17), so changes go unverified locally (P0 #4) | Certain | High | Pinned local environment, revamp slice 1 | 3 |
| R11 (P2) | Unpinned dependencies change digits or break the suite. The CI matrix already resolves different NumPy and SciPy versions per Python version, because the latest of both need 3.12 or newer (P0 #3) | High | High | Decision 0003 (Python 3.12 and up) and 0005 (one universal uv.lock with hashes, `uv sync --locked`); decision 0007 (a tolerance per claim, byte equality only in the reference job) | 3 |
| R12 | Real data backtests inflated by zero latency fills and exchange timestamps (evaluation.py line 221; data.py line 125) (P0 #5) | Medium | High | Latency parameter, timestamp choice, results at both settings | 4 |
| R13 | Picking the best threshold on test data overstates the edge; Deflated Sharpe trial variance taken from non null trials (P0 #6) | Medium | Medium | Nested selection or a held out block used once | 4 |
| R14 | Real data studies on hand picked symbols and days (selection and survivorship) (P0 #7) | Medium | Medium | Written question and data record before each study | 1, 4 |
| R15 | Silent NaN to zero (signals.py line 127), NaN spreading in ewma (line 72), no ingestion checks, wrong timestamp units (P0 #8) | Medium | Medium | Validation at the loader with counts of rejected rows; unit check | 4, 5 |
| R16 | Most public functions do not validate inputs (for example risk.py historical VaR accepts an empty array) | Medium | Medium | Input checks at the public surface, with tests | 5 |
| R17 | A loose replication tolerance reads as tighter than it is (tests/test_alpha.py line 239, 4 percent gap) | Medium | Low | State the gap in the README next to the claim | 7 |
| R18 | No runtime budget; "45 s" is unmeasured (README lines 28, 172) | High | Low | Budgets in docs/requirements.md section 2; measure in Phase 3 | 3 |
| R19 | Single seed results presented without spread | High | Medium | Several seeds, mean and spread (revamp slice 7) | 4 |

## Security and supply chain (section 6, Tier A light)

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R20 (P2) | Supply chain: no lockfile or hashes, no audit, actions pinned by tag, no `permissions:` block in CI (P0 #10, widened) | Low | Medium | Decisions 0005, 0008, 0009: hashed uv.lock, actions pinned by commit, `permissions: contents: read`; audit step tool chosen in Phase 3 with approval | 3 |
| R21 | A secret in history is missed; history never scanned | Low | Medium | Secret scan of history and in CI | 3 |
| R22 | A large or hostile zip or CSV exhausts memory (data.py lines 64, 67) (P0 #9) | Low | Low | Size cap, streamed reading | 5 |
| R23 (P2) | Python 3.10 is past end of life (2026-10-01) but still declared and tested | Certain | Low | Decided: decision 0003 sets 3.12 and up, CI 3.12 to 3.14. Retired when the Phase 3 change lands | 3 |

## Cost and hosting (sections 8 and 10)

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R24 | Free CI terms change for public repositories | Low | Low | Ceiling is 0 USD; tests run locally as the fallback | 8 |
| R25 (P2) | The tier silently moves to B (package published or notebook hosted) without the extra checks. The PyPI name is already taken by another project | Low | Medium | Decisions 0008 and 0012: no package index release, no hosted notebook. Any change needs a new decision and a tier review | 2 (done), 7 |

## Process (section 11)

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R26 | Code the author cannot explain, given that much of it was machine drafted (P0 #14) | Medium | High | Five questions at each phase close; rebuild smaller where answers fail | all |
| R27 | Scope creep into new models before the evidence work is done (P0 #13) | High | Medium | Out of scope list in docs/brief.md; backlog | all |
| R28 (P2) | Version 1.0.0 promises a stable API that was never reviewed (P0 #11) | Medium | Medium | Decided: decision 0012 resets to 0.9.0 with a changelog; tag only with the author's yes | 3, 7 |
| R29 | A reader uses a price or risk number for a real decision (P0 #12) | Low | High | Known limitations section in the README | 7 |
| R30 (P2) | Overlap with zft-capital grows into two copies of the same statistics (P0 #15) | Low | Medium | Decision 0001; the Phase 2 design shares no code, data or tooling with zft-capital | 2 (done), all |
| R31 | Stale documentation: README test count and timings typed by hand | High | Medium | Generate them; fresh clone test at each phase close | 3, 7 |
| R32 | Never finishing: about 4 hours a week against a 2026-12-14 check date | Medium | Medium | Cut list: slices 1 to 3 first; others can slip | all |

## Phase 2 changes (2026-11-19)

Retired by the design, pending the Phase 3 change: R23 (Python floor decided). Decided but not yet implemented: R1, R8, R9, R11, R20, R25, R28. R2 is unchanged and still open; the design does not depend on a history rewrite.

New risks added by the design:

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R33 | Locking picks a release only days old (numpy 2.5.5 was uploaded 2026-11-15) that has a regression or a compromised file | Low | Medium | `uv lock --exclude-newer` about 14 days back; review every lock diff; hashes in the lock | 3, 8 |
| R34 | Numbers differ in the last digit between macOS and Linux, so the drift check flaps or tolerances are set too loose to catch real drift | Medium | Medium | Byte equality only in one reference job; per claim tolerances set from the measured gap (assumption 24), never wider than the claim's printed precision | 3, 4 |
| R35 | The claims registry falls behind the README, so a new number is published unchecked | Medium | High | The checker lists numbers in README tables that no claim covers and exits 2 | 4 |
| R36 | uv becomes unavailable or changes its lock format | Low | Low | Exit path: `uv export` to a hashed requirements file for plain pip (decision 0005) | 8 |
| R37 | The output guard is bypassed by copying a real data report into docs/ by hand | Low | High | Reports in local/ carry a CC BY NC SA notice and the source line in their header; the checker refuses a docs/metrics.json whose source kind is not simulated | 4 |
| R38 | Lowering the version from 1.0.0 to 0.9.0 confuses a reader who saw 1.0.0 | Low | Low | Changelog entry explains the reset; no release or tag ever existed | 3 |
| R39 | The first network install in Phase 3 is refused or delayed, so no test can run locally and the design stays unproven | Medium | High | Ask at the start of Phase 3 (assumption 27); the design needs one install only | 3 |


## Phase 3 changes (2026-11-22)

Status of earlier rows after the Phase 3 work in the worktree (uncommitted):
- R1: the guard and ignore rules exist (examples/report_io.py, alpha_research.py exit 3, .gitignore). The guard test through alpha_research.main is skipped without SciPy; the guard logic is tested with the standard library. Stays open until A9 passes in a full environment (slice 4.2).
- R20: `permissions: contents: read` and `persist-credentials: false` added. Still open: no lockfile, actions pinned by tag, no audit.
- R23: pyproject.toml and CI now say 3.12 and up. Retire once CI runs green on 3.12 to 3.14.
- R28, R38: version is 0.9.0 with CHANGELOG.md.
- R39: happened in part. The install was not done in this session, so no existing test ran; the work that needs no network was done and the rest is marked blocked.

New risks:

| # | Risk | Likelihood | Damage | Mitigation | Phase |
|---|---|---|---|---|---|
| R40 | Moving showcase.py's body into `main()` changed its output in a way ruff and a syntax check cannot see; it was not run (no SciPy) | Low | Medium | The move was mechanical (indent only, plus `--out`, metrics and one unused line removed); `git diff -w` shows the logic is untouched. First full run: compare docs/RESULTS.md with `git diff` | 3 |
| R41 | docs/metrics.json was computed with `math.erfc`, not by showcase.py; if SciPy's value prints a different sixth decimal the first check fails | Low | Low | 10.450583572185565 sits 7e-8 from the nearest rounding edge, far above float error; regenerate with `tools/reproduce.py` on the first full run | 3 |
| R42 | Until uv.lock lands, CI installs the newest packages with pip, so a new upstream release can turn CI red or move a digit | Medium | Medium | The reproduce job compares within a tolerance; switch to `uv sync --locked` as soon as the install is approved (runbook section 5) | 3 |
| R43 | Runner names ubuntu-24.04 and macos-15 were written from memory; one may be retired or renamed, so a job never starts | Low | Low | Read the current GitHub runner image list before the first push (assumption 28) | 3 |
| R44 | The CI reproduce job runs before anyone has run showcase.py with the refactor, so its first result also tests R40 and R41 at once and a red run is hard to read | Medium | Low | Run `python tools/reproduce.py --check` locally first, once SciPy is installed | 3 |
