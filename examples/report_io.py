"""Output folders and the metrics file for the report scripts.

Standard library only, so it can be tested without NumPy, SciPy or matplotlib.

Rules (decisions 0002, 0006 and 0007):
- A simulated run writes to docs/ by default; those files are tracked.
- A real data run writes to local/runs/RUN_ID/ by default. local/ is git ignored. Any other
  output folder is refused with exit code 3, because Binance Vision data is CC BY NC SA 4.0
  and must not land in tracked files by accident.
- Every published number goes into DIR/metrics.json as {value, format}.
"""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LOCAL = ROOT / "local"

METRICS_SCHEMA_VERSION = 1
EXIT_OUTSIDE_LOCAL = 3  # exit code when a real data run points its output outside local/

# Binance Vision file names look like BTCUSDT-bookTicker-2024-03-01.zip
_BINANCE_NAME = re.compile(r"^(?P<symbol>[A-Z0-9]+)-[A-Za-z]+-(?P<date>\d{4}-\d{2}(?:-\d{2})?)")


class OutputOutsideLocalError(ValueError):
    """A real data run asked to write somewhere other than local/."""


def make_run_id(bookticker_path: str | Path, now: datetime | None = None) -> str:
    """RUN_ID = symbol, file date and a UTC timestamp, e.g. BTCUSDT_2024-03-01_20261119T1530Z."""
    now = now or datetime.now(UTC)
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%MZ")
    name = Path(bookticker_path).name
    match = _BINANCE_NAME.match(name)
    if match:
        return f"{match['symbol']}_{match['date']}_{stamp}"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem) or "run"
    return f"{stem}_{stamp}"


def is_inside(path: Path, folder: Path) -> bool:
    """True when path is folder itself or below it, after resolving symlinks and '..'."""
    path, folder = path.resolve(), folder.resolve()
    return path == folder or folder in path.parents


def resolve_out_dir(out: str | Path | None, real_data: bool, run_id: str | None = None,
                    local_root: Path = LOCAL, docs_root: Path = DOCS) -> Path:
    """Pick the output folder for one run, or raise OutputOutsideLocalError.

    out: the --out argument, or None for the default.
    real_data: True when the run reads Binance files instead of the simulator.
    run_id: folder name under local_root/runs for the real data default.
    """
    if not real_data:
        return Path(out).resolve() if out is not None else docs_root.resolve()
    target = Path(out) if out is not None else local_root / "runs" / (run_id or "run")
    if not is_inside(target, local_root):
        raise OutputOutsideLocalError(
            f"real data output must stay under {local_root} (git ignored); got {target.resolve()}. "
            "Binance Vision data is CC BY NC SA 4.0 and must not be written to tracked files."
        )
    return target.resolve()


def write_metrics(out_dir: Path, generator: str, metrics: dict[str, tuple[float, str]]) -> Path:
    """Merge metrics from one generator into out_dir/metrics.json and return its path.

    metrics maps a metric id to (value, format spec), e.g. {"bs.atm_call": (10.4505..., ".6f")}.
    Entries from other generators already in the file are kept; this generator's old entries
    are replaced, so a metric removed from a script also leaves the file.
    """
    path = out_dir / "metrics.json"
    data = {"schema_version": METRICS_SCHEMA_VERSION, "metrics": {}}
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("schema_version") == METRICS_SCHEMA_VERSION:
            data["metrics"] = {k: v for k, v in old.get("metrics", {}).items() if v.get("generator") != generator}
    for metric_id, (value, fmt) in metrics.items():
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"metric {metric_id} is not finite: {value}")
        format(value, fmt)  # fail early on a bad format spec
        data["metrics"][metric_id] = {"value": value, "format": fmt, "generator": generator}
    data["metrics"] = dict(sorted(data["metrics"].items()))
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
