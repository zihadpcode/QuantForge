# 0010: Background work

Date: 2026-11-19. Status: proposed in Phase 2, awaiting approval. Options table: docs/design.md section 1.8.

## Decision

Does not apply as a service. Keep CI on push and pull request and add `workflow_dispatch` for a manual run. No worker or queue. A weekly scheduled lock refresh waits for the Phase 8 update routine; with a locked build, a schedule now would find nothing new to break.

## What would change this

Studies that take longer than a CI job allows, or the Phase 8 update schedule.
