# Runbook

How to set up, test, regenerate the published numbers, run a real data study and roll back.
Started 2026-11-22 in Phase 3. Tier A: nothing is deployed; the only remote machine is GitHub Actions.

## 1. Set up

Target (decision 0005), once `uv.lock` is committed:

```sh
uv sync --locked --extra dev      # builds .venv from uv.lock; fails if the lock is out of date
```

Until then (today), the old way still works where SciPy can be installed:

```sh
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"           # dev includes the examples extra (matplotlib)
```

Python 3.12 or newer is required (decision 0003). Extras: `examples` adds matplotlib for
examples/ and the notebook; `dev` adds the test oracles, pytest, ruff and `examples` (decision 0004).

### Creating the lock (blocked: needs the author's yes for a network install from PyPI)

Run once, with the cool off date set about 14 days before the day you lock (R33):

```sh
uv lock --exclude-newer 2026-11-09T00:00:00Z   # example date for a lock made on 2026-11-23
uv sync --locked --extra dev
uv run pytest                                  # A4: prints the test count; time it three times (A16)
```

Then read uv.lock: each wheel and sdist should carry a sha256 hash (assumption 22), and nothing
should build from source (assumption 23).

## 2. Check

```sh
ruff check src tests examples tools
pytest
python tools/reproduce.py --check      # exit 0 means every metric and claim reproduces
```

With uv, prefix each with `uv run`. Exit codes of the check: 0 pass; 1 a metric drifted or its
printed digits changed; 2 a README claim is missing or disagrees with its metric; 3 metrics.json or
claims.toml is missing, unreadable or of an unknown schema_version; 4 with `--reference`, a Markdown
report is not byte equal.

Without SciPy (the author's Mac today), the standard library tests still run:

```sh
python3.12 -m unittest tests/test_project_config.py tests/test_report_io.py tests/test_reproduce.py tests/test_alpha_outputs.py
```

## 3. Regenerate the published reports

```sh
python tools/reproduce.py              # runs showcase.py and alpha_research.py into docs/
git diff --stat docs/                  # review every changed number before committing
```

Each script also runs alone: `python examples/showcase.py [--out DIR]` and
`python examples/alpha_research.py [--out DIR]`. Both write `metrics.json` into their output
folder (only showcase so far, metric `bs.atm_call`).

### Adding a published number

1. Make the script put the value into `write_metrics(...)` with its format spec.
2. Regenerate so docs/metrics.json has it.
3. Add a `[[claim]]` to docs/claims.toml with the exact README text and a tolerance.
4. `python tools/reproduce.py --check` must exit 0.

## 4. Real data study (local only)

Raw Binance Vision files go in `data/` (git ignored). They are CC BY NC SA 4.0; this repository
is MIT (decision 0002).

```sh
python examples/alpha_research.py --bookticker data/BTCUSDT-bookTicker-2024-03-01.zip \
                                  --aggtrades  data/BTCUSDT-aggTrades-2024-03-01.zip
```

Output goes to `local/runs/RUN_ID/` (git ignored). `--out` outside `local/` exits with code 3
and writes nothing. After a run, `git status --porcelain` must show no new or changed file.

## 5. CI

`.github/workflows/tests.yml`: a test job on ubuntu-24.04 with Python 3.12, 3.13, 3.14 plus
macos-15 with 3.12, and a reproduce job on ubuntu-24.04 with 3.12. Read only token, manual
trigger. Steps still open (docs/progress.md slice 3.4):

- Pin each action by commit. Look up the commit of the tag in use, then write
  `uses: actions/checkout@<40 hex commit> # v4.x.y`. Lookup command (network, read only):
  `git ls-remote https://github.com/actions/checkout 'refs/tags/v4*'`.
- After uv.lock exists, replace setup-python and pip in each job with:

  ```yaml
  - uses: astral-sh/setup-uv@<commit>  # tag
    with:
      python-version: ${{ matrix.python-version }}
      enable-cache: true
  - run: uv sync --locked --extra dev
  - run: uv run ruff check src tests examples tools
  - run: uv run pytest
  ```

  and in the reproduce job `uv run python tools/reproduce.py --check --reference` (add
  `--reference` only after Phase 4 slice 4.1 removes wall times from docs/RESULTS.md).
- Secret scan and dependency audit: each tool picked from an options table and approved first.

## 6. Release

No package index release (the name is taken; tier stays A). A git tag `v0.9.0` is a push and waits
for the author's yes in Phase 7. Update CHANGELOG.md first.

## 7. Roll back

Nothing is deployed. Revert the commit (`git revert <id>`) and push when pushing is allowed.
To undo uncommitted work in the worktree: `git restore <file>` for tracked files and delete new
files by hand. Generated docs are restored by `git restore docs/`.
