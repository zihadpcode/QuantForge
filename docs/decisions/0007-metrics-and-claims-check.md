# 0007: Reproduction and drift check

Date: 2026-11-19. Status: accepted 2026-11-22 (proposed in Phase 2). Options table: docs/design.md section 1.5. Contracts: docs/design.md section 3.5.

## Decision

Change from hand typed README numbers to a checked chain:

1. Each report script writes every published number to docs/metrics.json as a value and a format.
2. docs/claims.toml ties each README number to a metric id, its exact README text and a tolerance.
3. `uv run python tools/reproduce.py` regenerates everything in place. `--check` regenerates into a temporary folder, compares numbers within tolerance, checks every claim string is in README.md, flags README numbers no claim covers, and counts collected tests in process. `--reference` adds byte for byte equality of the Markdown reports, used only in the CI reference job (Ubuntu, Python 3.12, locked).
4. Wall times leave the published tables. Figures are regenerated, not compared byte for byte.

## Why change

The success outcome (100 percent of published numbers regenerate) and R9, R31 fail today. README lines 81 and 82 are printed by no script; acceptance tests A2 and A3 fail.

## Options beaten

A plain text diff (flaps on the last digit across platforms and leaves the README unchecked); a templated README (awkward to edit by hand); no check (fails the number).

## What would change this

If the README grows many more numbers, generating it from a template may become cheaper than keeping the registry.
