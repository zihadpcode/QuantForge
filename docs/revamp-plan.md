# Revamp plan

Date: 2026-11-16. Updated 2026-11-19 in Phase 2 so the Phase 3 and Phase 4 slices match docs/design.md. Phase 2 approved 2026-11-22. Phase 3 slice status lives in docs/progress.md (3.3 done; 3.1, 3.4 and 3.5 partly done; 3.2 blocked).

## Where the project stands against Phases 1 to 8

| Phase | Status | Evidence |
|---|---|---|
| 0 Frame | Approved 2026-11-17 | docs/brief.md |
| 1 Requirements and risk | Approved 2026-11-19 | docs/requirements.md, docs/threat-model.md, docs/risks.md, docs/acceptance-tests.md |
| 2 Design | Drafted, awaiting approval | docs/design.md, decisions 0003 to 0012 |
| 3 Scaffold | Partly met | src layout, ruff, pytest and a CI matrix exist (.github/workflows/tests.yml). Missing: lockfile, type check, secret scan, dependency audit, a local environment that runs |
| 4 Build | Largely met | 14 modules plus `alpha`, 80 test functions. Tests were not run in Phase 0, so "met" rests on the CI badge only |
| 5 Harden | Not met | No written pass for inputs, dependencies or runtime |
| 6 Deploy and operate | Skipped for Tier A | Becomes a release step only if the package is published |
| 7 Validate | Not met | README numbers are not checked against a fresh clone |
| 8 Maintain | Not met | No dependency update schedule, no retro |

## Restructuring proposed

Layout and naming:
- Keep the src layout and module names. No renames proposed; the public names are already in the README.
- Add `alpha` to the top level imports and `__all__` in src/quantforge/__init__.py, or state in the docstring that it is imported separately.
- Move matplotlib from the dev extra to a new `examples` extra, so the examples have a documented install.
- Rename docs/RESULTS.md and docs/ALPHA_RESULTS.md only if wanted; they are generated files and should say so in a header. No move proposed.
- Add docs/runbook.md (how to set up, test, regenerate results, cut a release). The architecture diagram now lives in docs/design.md section 7.
- Phase 2 adds tracked docs/metrics.json and docs/claims.toml, and git ignored data/ and local/ (decision 0006).

Dead code and duplicates:
- No dead modules or duplicate copies found in the tracked tree by reading the file list. The .gitignore line for `*.bundle` suggests bundles existed locally once; none are tracked.
- README.md repeats the validation table from docs/RESULTS.md by hand. Replace the hand copy with a checked copy (decision 0007, Phase 4 slice 4.1).

Authorship fix (needs an explicit yes, see docs/current-state.md). Status 2026-11-19: the rewrite is not approved, and the Phase 3 and 4 plans below do not depend on it. Until the author decides, the middle option (leave history, keep new commits clean) is what happens by default:

| Option | Cost | Risk | Reversible | Pick when |
|---|---|---|---|---|
| Rewrite all 10 commits and force push | 30 minutes | Commit ids change; clones must re-sync | Only from the backup bundle | The rule must hold for the whole history. Recommended, since the repository is young and has one user |
| Leave history, set git config and hooks so new commits are clean | 10 minutes | Old commits still show the tool | Yes | A force push is not acceptable |
| Squash into one new root commit by the human author | 15 minutes | Loses the history of fixes | Only from the backup bundle | History has no value to keep |

Relation to zft-capital: stay separate. See docs/decisions/0001.

## Phase 3 slices: scaffold and walking skeleton

Each slice ends with a command and its expected output. Slice 3.1 needs the author's approval for one network install from PyPI (assumption 27). Ordered so the riskiest assumption from docs/brief.md (published numbers still reproduce) is tested as early as possible.

1. 3.1 Python floor and lock (decisions 0003, 0004, 0005). `requires-python >=3.12`, ruff target py312, `examples` extra, `uv lock --exclude-newer` about 14 days back, `uv sync --locked`. Check: `uv run pytest` on the Mac prints the collected test count and passes (A4); time it three times (A16). This is the cheapest experiment from the brief.
2. 3.2 First reproduction run, by hand. `uv run python examples/showcase.py` and `uv run python examples/alpha_research.py`, then `git diff --stat docs/`. Check: record which report lines change, and time each script (A17). Any change disproves the riskiest assumption and is logged before anything is fixed.
3. 3.3 Ignore rules and version (decisions 0006, 0012). Add `data/`, `local/`, `*.zip`, `*.csv` to .gitignore; version 0.9.0; CHANGELOG.md. Check: `git check-ignore data/x.zip local/runs/a/report.md` prints both paths (A13).
4. 3.4 CI rework (decisions 0008, 0009, 0010). setup uv action pinned by commit, `uv sync --locked`, matrix Ubuntu 3.12, 3.13, 3.14 plus macOS 3.12, exact runner image names, `permissions: contents: read`, `workflow_dispatch`. Secret scan of history and a dependency audit step, with each tool chosen by options table and approved before it is added. Check: all jobs green on a branch push (when pushes are allowed); job times recorded (A18).
5. 3.5 Walking skeleton (docs/design.md section 8). One metric (`bs.atm_call`) in docs/metrics.json, one claim in docs/claims.toml, `tools/reproduce.py --check` with exit codes 0 to 3, the output guard on alpha_research.py with exit code 3, and the CI reference job. Check: green as is; a branch with one edited digit is red.

Rollback for Tier A: revert the commit; nothing is deployed.

## Phase 4 slices: vertical slices, by value and risk

1. 4.1 Every published number from code (decision 0007, R9, R35). Every README number gets a claim; add the 40 run false positive count ("34 / 40", "4 / 40") to alpha_research.py; test count from in process collection; wall times out of the tables; checker flags uncovered README numbers. Check: A1, A2, A3, A15 pass.
2. 4.2 Real data outputs kept local (decisions 0002, 0006, R1, R37). `--out`, default local/runs/RUN_ID, manifest.json, CC BY NC SA notice in local report headers, checker refuses a non simulated docs/metrics.json. Test with a tiny synthetic Binance shaped file. Check: A9 passes, `git status --porcelain` empty after a real data run.
3. 4.3 Loader contract (decision 0011, docs/design.md section 3.2). Size cap, timestamp unit detection, row validation with IngestReport, `time_field` choice; stop NaN becoming zero in `order_flow_imbalance`. Check: A11, A20 (cap part); one test per error case in the contract table.
4. 4.4 Latency in the backtest (R12). `latency_steps` with default 0; real data path reports 0 and 1. Check: A10; published simulated numbers unchanged (reproduce check green).
5. 4.5 Input validation at the public surface (R16). Check: A6.
6. 4.6 Uncertainty across seeds (R19). Mean and spread for R squared, IC and break even fee as new metrics and claims.
7. 4.7 Notebook in CI (A8), `alpha` in the top level `__all__`, `py.typed`, type check in CI.
8. 4.8 Research record template for any real data study (A12, R14). Written before a download; no download in this slice.

Not planned: the authorship history rewrite. It is not approved (assumption 11, R2). New commits use the human identity and carry no AI trailers.

Not yet, and why: new models, speed work, a package index release, a hosted notebook. None of them moves the success outcome in docs/brief.md, and the last two move the tier to B.
