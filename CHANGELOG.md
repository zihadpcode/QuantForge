# Changelog

All notable changes to this project are listed here. Versions follow semantic versioning. While the
version is below 1.0, the public API is not yet stable and a minor version may change it.

## 0.9.0 (not yet tagged)

The tag waits for the success outcome in docs/brief.md and the author's yes.

### Changed
- Version reset from 1.0.0 to 0.9.0. No 1.0.0 release or tag was ever made (decision 0012).
- Python 3.12 or newer is required; 3.10 and 3.11 are no longer supported (decision 0003).
- matplotlib moved from the `dev` extra to a new `examples` extra; `dev` includes `examples`
  (decision 0004).
- CI: Ubuntu with Python 3.12, 3.13 and 3.14 plus one macOS job with 3.12, a read only token and
  a manual trigger (decision 0008).
- `examples/showcase.py` and `examples/alpha_research.py` take `--out DIR` and expose
  `main(argv) -> int`.

### Added
- Ignore rules for raw data and local run outputs: `data/`, `local/`, `*.zip`, `*.csv`
  (decision 0006).
- A real data run of `examples/alpha_research.py` writes to `local/runs/RUN_ID/` by default and
  exits with code 3 if its output folder is outside `local/` (decisions 0002 and 0006).
- `docs/metrics.json`, `docs/claims.toml` and `tools/reproduce.py` with `--check`, starting with
  one metric, `bs.atm_call` (decision 0007).
- docs/runbook.md.

