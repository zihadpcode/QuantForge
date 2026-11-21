# Assumptions

Each line is believed, not proven. Rows 1 to 9 added 2026-11-16 (Phase 0). Rows 10 to 20 added 2026-11-17 (Phase 1). Rows 21 onward added 2026-11-19 (Phase 2).

On 2026-11-19 the author approved the Phase 1 drafts with every default as written. The Phase 1 defaults (rows 10 to 20) are marked accepted 2026-11-19. Accepted means the author took the default; it does not make the belief proven.

| # | Assumption | Basis | How to check |
|---|---|---|---|
| 1 | origin/main is the live line of work | Only branch, local and remote; working tree was clean | Ask the author |
| 2 | The project is a learning and portfolio library, not a tool for real trades | README wording, single author, no releases | Ask the author |
| 3 | Author profile (student, about 4 hours a week, zero budget, Apple Silicon Mac) carries over from the zft-capital brief | ~/zft-capital/PROJECT_BRIEF.md section 2 | Ask the author |
| 4 | The CI badge is green and the suite has 96 collected tests | README only; 80 test functions and 9 parametrize uses were counted | Run pytest in a pinned environment |
| 5 | Committed docs/RESULTS.md and docs/ALPHA_RESULTS.md match what the scripts produce today | Read, not run | Slice 1 and 2 in docs/revamp-plan.md |
| 6 | No real Binance data has been used for any published number | Reports say simulated; no data files tracked, and none in any commit (checked 2026-11-17 with `git log --all --name-only`) | Ask the author |
| 7 | The package is not on a package index | Checked 2026-11-17: the name `quantforge` on PyPI belongs to a different, unrelated project (version 0.1.1, a Rust based option pricer, uploaded 2025-09-26). https://pypi.org/pypi/quantforge/json | Resolved for this repository: it is not published. See row 12 |
| 8 | Runtime dependencies stay limited to NumPy and SciPy | pyproject.toml line 12 | Ask the author |
| 9 | Nobody else has cloned or forked the repository, so a history rewrite disturbs no one | Not checked on the remote | Check forks and clones on the host before any rewrite |

## Defaults taken for the Phase 0 open questions

The author approved the brief on 2026-11-17 and asked that the defaults proposed in the brief be used for each open question. Each one below was a default; all were accepted 2026-11-19.

| # | Open question (docs/brief.md) | Default answer | Where the default comes from | Status |
|---|---|---|---|---|
| 10 | Who is the audience? | The author first, then readers of the public repository (portfolio readers, other students). Docs are written for a reader who knows Python and basic statistics | docs/brief.md problem statement, "Who" | Accepted 2026-11-19 |
| 11 | Approve a history rewrite to remove the tool author and trailers? | Not approved. History stays as it is. The authorship problem is recorded as a risk (docs/risks.md R2) and an open decision. No rewrite, force push or squash is done. New commits, when commits are allowed, use the human identity and carry no AI trailers | Task instruction for Phase 1; working agreement section 3 | Accepted 2026-11-19. Rewrite still not approved; open decision |
| 12 | Will the package be published to a package index? | No. The project stays Tier A: laptop plus a public source repository. Note: the name `quantforge` is already taken on PyPI by another project, so a future release would need a different distribution name | docs/brief.md "Not yet: a package index release"; PyPI check above | Accepted 2026-11-19 |
| 13 | Hours per week and deadline? | About 4 hours a week. Success check date 2026-12-14 | docs/brief.md success outcome; zft-capital brief section 2 | Accepted 2026-11-19 |
| 14 | Is version 1.0.0 a stable public API promise? | No, not until a Phase 2 decision either tags 1.0.0 with a changelog or resets the version below 1.0. Until then the README should not imply a stable API | docs/risks.md R11 (decide in Phase 2); revamp plan slice 8 | Accepted 2026-11-19 |
| 15 | Has the pipeline run on real Binance files, and are those results meant to be published? | Assume never run for any published number. Real data runs stay personal research on the laptop; their raw files and outputs stay out of git. Publishing any real data result needs a written research record first and must follow the Binance Vision Dataset Terms (CC BY NC SA 4.0, attribution, noncommercial). See docs/decisions/0002 | Assumption 6; Binance Vision Dataset Terms checked 2026-11-17 | Accepted 2026-11-19 |

## Other assumptions added in Phase 1

Rows 16 to 20: accepted 2026-11-19 as defaults. Rows 17, 18 and 20 still need checking before any real data download.

| # | Assumption | Basis | How to check |
|---|---|---|---|
| 16 | Monthly cost ceiling is zero | zft-capital brief states zero budget; GitHub Actions standard runners are free for public repositories (https://docs.github.com/en/billing/concepts/product-billing/github-actions, checked 2026-11-17); Binance Vision files are free of charge (Dataset Terms 2.3) | Ask the author |
| 17 | Showing QuantForge to recruiters or in a portfolio is not "commercial use" of Binance data under CC BY NC SA 4.0, as long as no real data result is sold or used for paid signals | CC BY NC SA defines commercial use as "primarily intended for commercial advantage or monetary compensation" (https://creativecommons.org/licenses/by-nc-sa/4.0/). Not legal advice; not checked with a lawyer | Ask the author; only matters once real data results are published |
| 18 | Binance futures daily files still use millisecond timestamps | The loader assumes milliseconds (data.py lines 7 to 10). Binance switched SPOT archive files to microseconds from 2025-01-01 (https://github.com/binance/binance-public-data, checked 2026-11-17). No official statement found for futures | Inspect one real futures file before any real data study |
| 19 | The author's laptop has at least 8 GB of memory | Not checked | Ask the author |
| 20 | The author's location does not bar use of Binance Vision files | Binance's list of prohibited countries forms part of its Terms of Use (https://www.binance.com/en/legal/list-of-prohibited-countries/, page dated 2024-02-27, checked 2026-11-17). Whether downloading public archive files counts as using Binance services was not determined | Author confirms; read the current Binance Terms of Use before downloading |

## Assumptions added in Phase 2

| # | Assumption | Basis | How to check |
|---|---|---|---|
| 21 | No outside user needs Python 3.10 or 3.11 | Assumption 2; no package index release; no issues checked | Ask the author; watch for issues after the floor moves |
| 22 | `uv.lock` records a sha256 hash for every wheel and sdist, and `uv export` writes hashes by default | `uv export --help` lists `--no-hashes`; a uv 0.13 lockfile on this machine carries hashes (2026-11-19). The uv documentation pages read did not state it | Read the generated uv.lock in Phase 3 |
| 23 | matplotlib, scikit-learn and statsmodels ship wheels for Python 3.12, 3.13 and 3.14 on macOS arm64 and Linux x86_64 | Their PyPI floors are 3.11 and 3.10 (checked 2026-11-19); wheel lists not checked | `uv lock` resolves without building from source; read the lock |
| 24 | Published numbers agree between macOS arm64 and Linux x86_64 within small tolerances, but not always to the last printed digit | Different BLAS builds and instruction sets; not measured | Run `reproduce.py --check` on both in Phase 3 and record the largest gap per metric |
| 25 | Test run, both scripts and the check each fit the budget split in docs/design.md section 4 | README says about 45 s for tests and showcase on an unnamed machine; nothing measured | Time each step in Phase 3 |
| 26 | Each published Markdown report is byte for byte identical on repeated runs in the reference environment | Seeds are fixed; no wall time once decision 0007 lands | Run the reference job twice |
| 27 | Phase 3 gets approval for one network install from PyPI (to create the lock and the environment) | Required by decision 0005; not yet asked | Ask the author at the start of Phase 3 |

