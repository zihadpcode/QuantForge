# 0006: Data store and output layout

Date: 2026-11-19. Status: proposed in Phase 2, awaiting approval. Implements decision 0002 option A. Options table: docs/design.md section 1.4.

## Decision

Keep plain files in git; no database. Change where outputs go:

- Simulated reports stay at their tracked paths: docs/RESULTS.md, docs/ALPHA_RESULTS.md, docs/figures.
- New tracked files: docs/metrics.json (generated) and docs/claims.toml (hand written), see decision 0007.
- Raw Binance files live in data/, which git ignores.
- Any run given real data files writes to local/runs/RUN_ID/, which git ignores. The script exits with code 3 if the output folder resolves anywhere outside local/.
- New ignore rules: `data/`, `local/`, `*.zip`, `*.csv`.

## Why change

R1, T2 and acceptance tests A9 and A13 fail today: a real data run overwrites tracked files, and nothing ignores raw data. Binance Vision data is CC BY NC SA 4.0; the repository is MIT.

## What would change this

The author wants to publish a real data result: then decision 0002 option B (a separate CC BY NC SA folder with attribution and a research record), by a new decision.
