# 0012: Version and release

Date: 2026-11-19. Status: accepted 2026-11-22 (proposed in Phase 2). Options table: docs/design.md section 1.10.

## Decision

Change the version from 1.0.0 to 0.9.0 and add a changelog. Under semantic versioning, 0.y.z says the public API is not yet stable. No package index release: the name `quantforge` is taken on PyPI and a release would move the tier to B. A git tag is a push, so it waits for the author's yes, at the earliest when the success outcome is met (Phase 7).

## Why change

R28: 1.0.0 promises an API nobody reviewed. No tag or release exists, so nobody depends on 1.0.0 and the reset costs little.

## What would change this

The author reviews the public surface and wants to commit to it: then keep 1.0.0, write the changelog, and tag it.
