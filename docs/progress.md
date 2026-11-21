# Progress

Read this file first in every session.

Work location: git worktree at ~/projects/revamp/quantforge, branch revamp/phase-0, base origin/main at b1e33bc. Nothing is committed or pushed. Application code is unchanged.

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

Status: in progress. All steps drafted; exit gate awaiting approval. Documents only; no application code changed.

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

Exit gate: design approved, every major decision recorded. State: awaiting approval.

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

## Next action

The author reviews docs/design.md and decisions 0003 to 0012, and answers the five questions. Then "Close Phase 2" and "Start Phase 3". Phase 3 slice 3.1 needs a yes for one network install from PyPI to create uv.lock and the environment.

## Phases 3 to 8

Not started. Phase 3 and 4 slices are in docs/revamp-plan.md.
