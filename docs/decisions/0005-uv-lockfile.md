# 0005: Environment and lockfile

Date: 2026-11-19. Status: proposed in Phase 2, awaiting approval. Options table: docs/design.md section 1.3.

## Decision

Change from unpinned `pip install -e ".[dev]"` to uv with a committed `uv.lock`. Local and CI both run `uv sync --locked`, which fails when the lock is out of date. Lock with `--exclude-newer` set about 14 days back so a release only days old is not picked up at once.

## Why change

The 100 percent reproducibility number and R10, R11 fail without pinned versions. SciPy is missing locally, so the suite cannot run on the author's Mac.

## Options beaten

pip-tools (a file per Python and platform, easy to let drift), conda (different builds, larger toolchain), a container (heavy for a library and no native macOS run), unpinned pip (fails the number).

## Evidence

- uv 0.13.7 is already installed on the Mac (Homebrew, `uv --version`, 2026-11-19), so no new tool install is needed locally.
- https://docs.astral.sh/uv/concepts/projects/layout/ and https://docs.astral.sh/uv/concepts/projects/sync/ checked 2026-11-19: one universal lockfile across Python markers; `--locked` errors on a stale lock; export to requirements.txt, pylock.toml and CycloneDX.
- Hashes: `uv export --help` offers `--no-hashes`, so exports carry hashes by default; a uv 0.13 lockfile on this machine carries a sha256 per file. The documentation pages read did not state this.

## Exit path

`uv export --format requirements-txt` gives a hashed requirements file that plain pip can install with `--require-hashes`.

## Consequences

Creating the lock needs network access to PyPI. That is an install from the network and waits for the author's approval in Phase 3.
