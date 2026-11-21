# 0002: Where results derived from Binance data live

Date: 2026-11-17. Status: accepted 2026-11-19 with the Phase 1 approval: option A. Implemented by decision 0006 (Phase 2 design); code changes in Phases 3 and 4.

## Problem

The alpha study can run on Binance Vision files (examples/alpha_research.py lines 63 to 71). Those files are licensed CC BY NC SA 4.0 under the Binance Vision Dataset Terms, version 1.0, last updated 2026-08-26 (https://data.binance.vision/Binance_Vision-Terms_of_Use.pdf, checked 2026-11-17). Clause 2.4 says derived charts, models and indicators are governed by those terms. Clause 4.5 says a redistributed derivative work must credit Binance Vision and stay under CC BY NC SA 4.0. Clause 4.3 forbids hosting the datasets.

The repository is MIT licensed. Today a real data run writes its report to docs/ALPHA_RESULTS.md (line 241) and its figures to docs/figures (line 29), the same tracked paths as the simulated results. One `git add docs` would put CC BY NC SA material under an MIT repository without attribution. No such commit exists today (checked 2026-11-17).

## Options

| Option | Cost | Risk | Reversible | Pick when |
|---|---|---|---|---|
| A. Keep real data outputs local: a git ignored output folder for any non simulated run, plus `.gitignore` rules for raw files | About an hour in Phase 4: an output argument, two ignore rules, one test | Real data findings are never visible to readers | Yes | Real data use stays personal research. Default |
| B. Option A, plus a separate published folder (for example docs/real_data/) with its own LICENSE notice for CC BY NC SA 4.0, attribution to Binance Vision, download dates and the research record | A few hours per study | Must keep the two licenses apart; noncommercial limit applies to anyone reusing it; data can vanish (clause 5.3) | Yes, by deleting the folder in a later commit (history keeps it) | The author wants to publish a real data result |
| C. Remove the Binance loader and real data path | An hour | Loses the "runs on real data" feature in the README (line 77) | Yes, from git | The terms or the location question (assumption 20) rule out any use |
| D. Commit real data outputs into docs/ as today | None | Breach of clause 4.5 under the MIT license; reproducibility depends on files Binance may withdraw | Hard once public | Never recommended |

## Recommendation

Option A now, with B available later by a new decision when a real data result is worth publishing. It keeps the MIT repository clean, costs little, and blocks nothing.

What would change this: the author confirms that real data results are a goal of the portfolio (then plan B in Phase 2), or that the location or commercial questions (assumptions 17 and 20) rule out use (then C).
