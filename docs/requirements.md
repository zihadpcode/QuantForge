# Requirements

Phase 1. Date: 2026-11-17. Status: awaiting approval. Code read: origin/main at b1e33bc. Tier A (laptop only, public source repository, no personal data, money or credentials in the code).

QuantForge stays a separate project from zft-capital (docs/decisions/0001). Nothing here assumes shared code, data or tooling with it.

## 1. User flows

Ordered by value. At most seven.

### F1. Reproduce every published number from a fresh clone

- Actor: the author, or a reader of the public repository.
- Trigger: before a phase close, or a reader doubts a README number.
- Steps: clone the repository; create the pinned environment with the documented command; run one documented command that regenerates docs/RESULTS.md, docs/ALPHA_RESULTS.md, the figures and the README numbers; compare with the committed files.
- Result: every numeric claim in README.md, docs/RESULTS.md and docs/ALPHA_RESULTS.md matches within its stated tolerance, or the command names the claim that differs. This is the success outcome in docs/brief.md.

### F2. Verify correctness with the test suite

- Actor: the author locally; GitHub Actions on every push and pull request.
- Trigger: any code change.
- Steps: run ruff and pytest in the pinned environment; CI runs the same on its matrix.
- Result: a pass or fail with the count of tests run. Each model is checked against a closed form, a published benchmark or an independent method (README lines 5 to 10).

### F3. Price an instrument or measure risk through the library

- Actor: the author or a reader writing Python.
- Trigger: needs a price, Greek, implied volatility, surface fit, VaR or portfolio weight.
- Steps: import a function from `quantforge` (for example Black Scholes, Heston by Fourier, a PDE or tree, Monte Carlo, SVI, GARCH, historical VaR); pass arrays or scalars with stated units.
- Result: a number, or a clear error for invalid input (today most functions do not validate input; docs/current-state.md section 9).

### F4. Run the alpha study on simulated data

- Actor: the author or a reader.
- Trigger: wants to see the alpha method end to end.
- Steps: `python examples/alpha_research.py` with no arguments. It simulates a seeded book (examples/alpha_research.py lines 74 to 76), fits signals, runs walk forward evaluation, cost analysis and the market maker.
- Result: docs/ALPHA_RESULTS.md and docs/figures/alpha_*.png, every number computed. Negative results kept (the taker strategy loses after fees).

### F5. Learn the methods from the guide and the notebook

- Actor: a reader, or the author preparing to explain the code.
- Trigger: wants to understand a method, or prepares for the five questions at a phase close.
- Steps: read docs/ALPHA.md and README.md; open notebooks/quickstart.ipynb and run it in the pinned environment.
- Result: the notebook runs top to bottom with the stored outputs matching, and every claim in the guide is bounded by a test or a generated number.

### F6. Run the alpha study on real Binance files, as personal research

- Actor: the author only.
- Trigger: wants to test whether a signal survives real data.
- Steps: write the research question, symbol, dates and how they were chosen before downloading; download one day of bookTicker and aggTrades from data.binance.vision by hand, within its posted rate limits; run `python examples/alpha_research.py --bookticker ... --aggtrades ...`; keep raw files and outputs in a folder git ignores.
- Result: a local report that states latency and timestamp assumptions. Nothing derived from Binance data enters the MIT licensed repository unless decision 0002 is followed (CC BY NC SA 4.0, attribution to Binance Vision, noncommercial).
- Today: the script writes real data reports over the committed simulated report (examples/alpha_research.py line 241) and figures (line 29). See docs/decisions/0002.

### F7. Change code without breaking published claims

- Actor: the author.
- Trigger: a fix or a new feature.
- Steps: edit; run tests and the results drift check locally; push to a branch; CI repeats them.
- Result: CI fails if a test fails or any committed number drifts beyond tolerance; the author can explain the change.

## 2. Quality requirements

Tier A. A number is either backed by evidence named in the row, or marked target, user to confirm. "Not measured" means nobody has run it on the author's machine.

| Quality | Requirement | Applies? | Evidence or status |
|---|---|---|---|
| Reproducibility (the key number) | 100 percent of numeric claims in README.md, docs/RESULTS.md and docs/ALPHA_RESULTS.md regenerate from one command. Exact match in the same pinned environment; a per claim tolerance written next to each number for other platforms | Yes | Target from docs/brief.md, approved 2026-11-17. Today at least two claims (README lines 81 and 82) have no generating script |
| p95 response time per key path | Not applicable. There is no request path, server or user interface | No | Replaced by the runtime budgets below |
| Runtime budget, test suite | Full pytest run within 120 seconds wall time on the author's Mac, worst of 3 runs | Yes | Target, user to confirm. README says "about 45 s" on an unnamed machine (README lines 28, 172, 235); not measured |
| Runtime budget, report scripts | examples/showcase.py and examples/alpha_research.py (simulated) each within 10 minutes on the author's Mac | Yes | Target, user to confirm. Not measured. showcase.py uses up to 400,000 Monte Carlo paths (line 73) |
| Runtime budget, CI | One CI job within 15 minutes | Yes | Target, user to confirm. CI run times not checked |
| Availability target | Not applicable. Nothing is served. GitHub's own availability is accepted (section 8, Tier A) | No | |
| Data volume | Tracked repository under 10 MB packed. Simulated study 300,000 steps. Real data: one symbol, one day per run | Yes | Today 1.72 MiB packed (`git count-objects -vH`, 2026-11-17); figures 1.1 MB; 300,000 steps at examples/alpha_research.py line 74; one day per run from docs/ALPHA.md lines 353 to 356 |
| Memory | Peak memory of a real data run under 4 GB. The loader refuses an input above a size cap set after one real file is measured | Yes | Target, user to confirm. Not measured. Today the loader reads a whole zip member and all rows into memory with no cap (data.py lines 64 and 67) |
| Concurrency | Not applicable. One user, one process | No | |
| Monthly cost ceiling | 0 USD | Yes | Default, user to confirm (assumption 16). GitHub Actions standard runners are free for public repositories (checked 2026-11-17). Binance Vision files are free (Dataset Terms 2.3). No paid service exists |
| Recovery time | Not applicable as a service number. Substitute: a working environment rebuilt from a fresh clone within 30 minutes | Partly | Target, user to confirm. Not measured; depends on the pinned environment from revamp slice 1 |
| Acceptable data loss | Uncommitted local work since the last push. Generated reports: none lost, because they regenerate from seeds. Real data files: downloadable again only while Binance keeps them (Dataset Terms 5.3), so the research record keeps file names and checksums | Partly | Backups and restore rehearsal skipped for Tier A (docs/brief.md) |
| Supported platforms | macOS on Apple Silicon (the author's machine) and Ubuntu in CI | Yes | Target. CI covers Ubuntu only today (.github/workflows/tests.yml line 9) |
| Python versions | A supported set chosen in Phase 2 | Yes | pyproject.toml line 10 says 3.10 and up; CI tests 3.10 to 3.13 (tests.yml line 12). Python 3.10 reached end of life on 2026-10-01 (https://devguide.python.org/versions/, checked 2026-11-17). Latest NumPy 2.5.5 and SciPy 1.18.1 require Python 3.12 or newer (PyPI, checked 2026-11-17), so the 3.10 and 3.11 CI jobs install older versions and can print different digits |

Why the "No" rows do not apply: Tier A has no service, no network entry point and no other users (docs/brief.md, rigor tier). They become live if the tier moves to B, which happens if the package is published or the notebook is hosted.

## 3. Data classification

| Data | Class | Stored where | Who can read it |
|---|---|---|---|
| Source code, tests, examples, notebook, docs | Public | Laptop worktree; public GitHub repository | Anyone |
| Generated reports and figures from simulated data (docs/RESULTS.md, docs/ALPHA_RESULTS.md, docs/figures) | Public | Same as above | Anyone |
| Stored notebook outputs (17 cells) | Public | notebooks/quickstart.ipynb | Anyone |
| Raw Binance Vision files (bookTicker, aggTrades zips) | Internal. Public market data, but licensed CC BY NC SA 4.0 under the Binance Vision Dataset Terms, so redistribution carries conditions | Laptop only, in a folder outside git or git ignored. None tracked today (checked 2026-11-17) | Author only |
| Reports, figures and models derived from Binance files | Internal until published under decision 0002 | Laptop only, git ignored folder | Author only. If published: anyone, under CC BY NC SA 4.0 with attribution |
| Research record for real data studies (question, symbol, dates, file names, checksums) | Public | docs/ in the repository (to be created) | Anyone |
| Git author names and email addresses in commit metadata | Personal | Git history on the laptop and on GitHub | Anyone, because the repository is public. Already published in 10 commits |
| Git history authorship metadata naming an AI tool | Public | Git history | Anyone. Recorded as risk R2 |
| Author's GitHub credentials and tokens | Secret | Laptop credential store, never in the repository. Not inspected | Author only |
| CI token (`GITHUB_TOKEN`, issued per run by GitHub) | Secret | GitHub Actions runner, per job | The workflow; no `permissions:` block narrows it today (tests.yml has none) |
| Local virtual environment and caches (.venv, .pytest_cache) | Internal | Laptop, git ignored (.gitignore lines 1 to 4) | Author only |

No personal data of anyone other than the author is handled. The Binance datasets state they contain no personal data of retail users (Dataset Terms 9.2), and the terms forbid trying to re identify people from transaction ids.

## 4. Licenses, data rights and terms of service

All checked 2026-11-17 unless a row says otherwise. Not legal advice.

### Outside data

| Source | Used by | Terms | What it means here | Link |
|---|---|---|---|---|
| Binance Vision historical files (data.binance.vision): futures UM daily bookTicker and aggTrades | src/quantforge/alpha/data.py lines 3 to 18 and 117 to 126; examples/alpha_research.py lines 63 to 71; docs/ALPHA.md lines 350 to 367 | Binance Vision Dataset Terms, version 1.0, last updated 2026-08-26. Datasets are licensed CC BY NC SA 4.0 (clause 3.1). Supplemental to the Binance Terms of Use (1.1). Permitted: academic research, non monetized open educational projects, personal non production backtesting, noncommercial open source evaluations (4.1). Forbidden: live trading, paid signals, hosting or commercially exploiting the data or derived feeds (4.2 to 4.4). Redistributed derivative works must credit Binance Vision and stay under CC BY NC SA 4.0 (4.5). Derived charts, models and indicators are governed by these terms (2.4). Must respect rate limits; no scraping that dodges them (7.1, 7.2). Must not imply Binance endorsement (8.2). Binance may withdraw any dataset without notice (5.3). Amendments apply only to data downloaded after them (1.4) | 1. The library code (a loader) is not derived from the data and stays MIT. 2. Any figure, table or number computed from Binance files is a derivative work. Committing it to this MIT repository without a CC BY NC SA notice and attribution would breach 4.5. 3. Raw files should not be committed (4.3 forbids hosting; share alike would also apply). 4. Portfolio use is likely noncommercial (assumption 17), but not confirmed. 5. Keep the date of each download, because the terms in force at download govern that file. 6. The README may name Binance to describe file formats, without logos or any hint of endorsement | https://data.binance.vision/Binance_Vision-Terms_of_Use.pdf ; https://github.com/binance/binance-public-data (repository code is MIT; it points to TERMS_AND_CONDITIONS.md for the data) |
| Creative Commons BY NC SA 4.0 | Governs the Binance data | Attribution, noncommercial ("primarily intended for commercial advantage or monetary compensation"), share alike for adaptations, no added restrictions | See above | https://creativecommons.org/licenses/by-nc-sa/4.0/ |
| Binance Terms of Use and list of prohibited countries | Parent terms of the dataset terms | The prohibited countries list forms part of the Terms of Use; the copy found is dated 2024-02-27. The full current Terms of Use page did not load in this check | Whether downloading public archives counts as using Binance services from a listed country was not determined. Assumption 20; the author confirms before downloading | https://www.binance.com/en/terms ; https://www.binance.com/en/legal/list-of-prohibited-countries/ |
| Published benchmark values (Fang and Oosterlee Heston values, Longstaff and Schwartz Table 1, Avellaneda and Stoikov results, Albrecher et al. form) | tests/test_heston_fourier.py line 23; tests/test_pde_trees_mc.py line 16; tests/test_alpha.py line 239; src/quantforge/heston.py line 9 | Numbers and formulas quoted from papers with citation | Facts and formulas, cited. No text or figures copied was found by reading. Keep the citations | Papers as cited in the code |
| Simulated data | All published results | Generated by the repository's own seeded code | No outside rights | examples/alpha_research.py line 74; examples/showcase.py |

No other outside dataset or API was found. A grep of src, tests and examples for network libraries, pickle, eval and subprocess found none (2026-11-17).

### Key dependencies

| Package | Role | License | Latest seen | Link |
|---|---|---|---|---|
| NumPy | Runtime | BSD 3 Clause plus bundled 0BSD, MIT, Zlib, CC0 1.0 | 2.5.5, 2026-11-15, needs Python 3.12 or newer | https://pypi.org/project/numpy/ |
| SciPy | Runtime | BSD style; wheels bundle OpenBLAS and LAPACK (BSD), GCC runtime (GPL 3.0 or later with the GCC runtime exception) and libquadmath (LGPL 2.1 or later) | 1.18.1, 2026-08-21, needs Python 3.12 or newer | https://pypi.org/project/scipy/ |
| matplotlib | Examples and figures (dev extra) | Matplotlib license (PSF based) | 3.11.2 | https://pypi.org/project/matplotlib/ |
| scikit-learn | Test oracle (dev) | BSD 3 Clause | 1.9.1 | https://pypi.org/project/scikit-learn/ |
| statsmodels | Test oracle (dev) | BSD 3 Clause | 0.15.0 | https://pypi.org/project/statsmodels/ |
| pytest | Tests (dev) | MIT | 9.2.0 | https://pypi.org/project/pytest/ |
| ruff | Lint (dev) | MIT | 0.17.5 | https://pypi.org/project/ruff/ |
| setuptools, wheel | Build | MIT | not checked | https://pypi.org/project/setuptools/ |
| actions/checkout v4, actions/setup-python v5 | CI | MIT (not rechecked today) | pinned by tag, tests.yml lines 14 and 15 | https://github.com/actions/checkout |
| GitHub Actions hosting | CI | Standard runners free in public repositories | | https://docs.github.com/en/billing/concepts/product-billing/github-actions |

All are permissive and compatible with the MIT license of QuantForge (LICENSE). None is copied into the repository; they are installed. The GPL and LGPL parts inside SciPy wheels carry their own exceptions and do not change QuantForge's license, because QuantForge does not ship SciPy.

### Prior art carried over from Phase 0

Phase 0 asked for maintenance dates to be confirmed in Phase 1.

| Library | Latest release | License | Note | Link |
|---|---|---|---|---|
| QuantLib (Python) | 1.44, 2026-10-13 | BSD 3 Clause | Maintained. Usable as a test oracle | https://pypi.org/project/QuantLib/ |
| FinancePy | 1.1.2, 2026-08-21 | GPL 3.0 or later | Maintained. Do not copy its code into this MIT repository. Using it only as an installed test oracle in the dev group keeps QuantForge's code MIT, but adds a GPL tool to the test chain; decide in Phase 2 if it is ever wanted | https://pypi.org/project/financepy/ |

### This repository's own name and license

- License: MIT (LICENSE line 1; pyproject.toml line 11). Copyright line reads "quantforge contributors".
- PyPI name: `quantforge` is taken by an unrelated project (assumption 7). Matters only if publishing is ever approved.
