# 0011: Data source

Date: 2026-11-19. Status: proposed in Phase 2, awaiting approval. Options table: docs/design.md section 1.9.

## Decision

Keep simulated, seeded data as the only source of published numbers. Keep the Binance Vision loader for personal research on the laptop and harden it in Phase 4: timestamp unit check (A11), a size cap set from one measured file (A20), row validation with counts (R15), a choice of `transaction_time` or `event_time`, and a `latency_steps` argument in the backtest whose default of 0 leaves published simulated numbers unchanged (A10, R12). Every real data run writes a manifest with file names, sha256 and download date (R6, R14).

## Why keep

Nothing in Phase 1 shows simulated publication failing. The loader fails the real data acceptance tests, which calls for hardening, not replacement.

## Constraints

No download happens before a written research record and the author's confirmation of assumptions 17, 18 and 20. Binance Vision Dataset Terms (CC BY NC SA 4.0) as recorded in docs/requirements.md section 4 and decision 0002.
