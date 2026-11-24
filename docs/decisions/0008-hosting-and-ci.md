# 0008: Hosting and CI

Date: 2026-11-19. Status: accepted 2026-11-22 (proposed in Phase 2). Options table: docs/design.md section 1.6.

## Decision

Hosting a service does not apply: nothing is served. Keep the public GitHub repository and GitHub Actions standard runners. Change the CI layout: a test job on Ubuntu with Python 3.12, 3.13 and 3.14 plus one macOS job with 3.12 (A24), and one reference job running the reproduce check. Actions pinned by commit, runner images named exactly, `permissions: contents: read`. No package index release and no hosted notebook (both would move the tier to B, R25).

## Evidence

https://docs.github.com/en/billing/concepts/product-billing/github-actions checked 2026-11-19: standard GitHub hosted runners are free in public repositories; larger runners are billed even there; GitHub Free includes 500 MB artifact storage and 10 GB cache per repository. No minute limit is stated for public repositories on that page. Concurrent job limits were not checked.

## Exit path

All checks run locally with the same commands, so losing free CI costs speed, not ability.
