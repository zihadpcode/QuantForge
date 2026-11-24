"""Regenerate the published reports, or check that every published number still reproduces.

    python tools/reproduce.py                      # regenerate docs/ reports, figures, metrics.json
    python tools/reproduce.py --check              # regenerate into a temporary folder and compare
    python tools/reproduce.py --check --reference  # also require byte equal Markdown reports

Exit codes (docs/design.md section 3.5):
    0  regenerated, or every check passed
    1  a metric moved outside its tolerance, or its printed digits changed
    2  a claim's text is missing from README.md, or disagrees with its metric
    3  docs/metrics.json or docs/claims.toml is missing, unreadable or has an unknown schema_version
    4  with --reference, a Markdown report differs byte for byte from the committed one

The report scripts run in this process through their main(argv) function; no subprocess is used.
The checking part needs only the standard library; regenerating needs the full environment.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXAMPLES = ROOT / "examples"
README = ROOT / "README.md"

SCHEMA_VERSION = 1
# Used for a metric that no claim covers. Tight, so an unexplained change is still caught.
DEFAULT_REL_TOL = 1e-9

EXIT_OK, EXIT_DRIFT, EXIT_CLAIM, EXIT_CONFIG, EXIT_REFERENCE = 0, 1, 2, 3, 4


@dataclass(frozen=True)
class Generator:
    """One report script: its file and the Markdown reports it writes into its output folder."""

    name: str
    script: Path
    reports: tuple[str, ...]


# Scripts run by --check: only those that write metrics so far. alpha_research joins in slice 4.1.
CHECK_GENERATORS = (Generator("showcase", EXAMPLES / "showcase.py", ("RESULTS.md",)),)
# Scripts run by a plain regenerate, writing into docs/.
ALL_GENERATORS = CHECK_GENERATORS + (
    Generator("alpha_research", EXAMPLES / "alpha_research.py", ("ALPHA_RESULTS.md",)),
)


class ConfigError(Exception):
    """metrics.json or claims.toml cannot be used (exit code 3)."""


@dataclass(frozen=True)
class Claim:
    id: str
    metric: str
    readme_text: str
    abs_tol: float | None = None
    rel_tol: float | None = None

    def within(self, old: float, new: float) -> bool:
        return math.isclose(old, new, rel_tol=self.rel_tol or 0.0, abs_tol=self.abs_tol or 0.0)


# ---- reading the two registries ------------------------------------------------


def load_metrics(path: Path) -> dict[str, dict]:
    """Return {metric id: {"value", "format", ...}} from a metrics.json, or raise ConfigError."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ConfigError(f"{path} is missing") from err
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ConfigError(f"{path} is unreadable: {err}") from err
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        version = data.get("schema_version") if isinstance(data, dict) else None
        raise ConfigError(f"{path} has schema_version {version!r}; this tool reads {SCHEMA_VERSION}")
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        raise ConfigError(f"{path} has no 'metrics' table")
    for metric_id, entry in metrics.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("value"), int | float) or "format" not in entry:
            raise ConfigError(f"{path}: metric {metric_id} needs a numeric 'value' and a 'format'")
    return metrics


def load_claims(path: Path) -> list[Claim]:
    """Return the claims in a claims.toml, or raise ConfigError."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ConfigError(f"{path} is missing") from err
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as err:
        raise ConfigError(f"{path} is unreadable: {err}") from err
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(f"{path} has schema_version {data.get('schema_version')!r}; this tool reads {SCHEMA_VERSION}")
    claims, seen = [], set()
    for raw in data.get("claim", []):
        missing = [k for k in ("id", "metric", "readme_text") if k not in raw]
        if missing:
            raise ConfigError(f"{path}: a claim is missing {', '.join(missing)}")
        if ("abs_tol" in raw) == ("rel_tol" in raw):
            raise ConfigError(f"{path}: claim {raw['id']} needs exactly one of abs_tol or rel_tol")
        if raw["id"] in seen:
            raise ConfigError(f"{path}: claim id {raw['id']} is used twice")
        seen.add(raw["id"])
        claims.append(Claim(raw["id"], raw["metric"], raw["readme_text"], raw.get("abs_tol"), raw.get("rel_tol")))
    return claims


# ---- the three checks --------------------------------------------------------------


def compare_metrics(committed: dict[str, dict], fresh: dict[str, dict], claims: list[Claim]) -> list[str]:
    """Problems found comparing committed metrics with freshly regenerated ones (exit code 1)."""
    by_metric = {c.metric: c for c in claims}
    problems = []
    for metric_id in sorted(committed.keys() | fresh.keys()):
        if metric_id not in fresh:
            problems.append(f"{metric_id}: committed but no longer generated")
            continue
        if metric_id not in committed:
            problems.append(f"{metric_id}: generated but not committed; run tools/reproduce.py and commit docs/")
            continue
        old, new = float(committed[metric_id]["value"]), float(fresh[metric_id]["value"])
        claim = by_metric.get(metric_id)
        ok = claim.within(old, new) if claim else math.isclose(old, new, rel_tol=DEFAULT_REL_TOL)
        if not ok:
            problems.append(f"{metric_id}: committed {old!r}, regenerated {new!r}")
            continue
        fmt = committed[metric_id]["format"]
        if format(old, fmt) != format(new, fmt):
            problems.append(f"{metric_id}: printed value changed from {format(old, fmt)} to {format(new, fmt)}")
    return problems


def check_claims(claims: list[Claim], metrics: dict[str, dict], readme: str) -> list[str]:
    """Problems found tying each claim to README.md and to its metric (exit code 2)."""
    problems = []
    for claim in claims:
        entry = metrics.get(claim.metric)
        if entry is None:
            problems.append(f"claim {claim.id}: metric {claim.metric} is not in metrics.json")
            continue
        printed = format(float(entry["value"]), entry["format"])
        if printed not in claim.readme_text:
            problems.append(f"claim {claim.id}: readme_text does not contain the metric as printed ({printed})")
        if claim.readme_text not in readme:
            problems.append(f"claim {claim.id}: README.md does not contain {claim.readme_text!r}")
    return problems


def compare_reports(committed_dir: Path, fresh_dir: Path, generators: tuple[Generator, ...]) -> list[str]:
    """Markdown reports that are not byte equal (exit code 4, --reference only)."""
    problems = []
    for gen in generators:
        for name in gen.reports:
            old, new = committed_dir / name, fresh_dir / name
            if not old.exists() or not new.exists() or old.read_bytes() != new.read_bytes():
                problems.append(f"{name}: regenerated report differs from the committed one")
    return problems


# ---- running the report scripts -------------------------------------------------------


def run_generator(gen: Generator, out_dir: Path) -> None:
    """Import one report script by path and call its main(["--out", out_dir])."""
    if str(EXAMPLES) not in sys.path:
        sys.path.insert(0, str(EXAMPLES))  # the scripts import their helper module report_io
    spec = importlib.util.spec_from_file_location(f"_reproduce_{gen.name}", gen.script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {gen.script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses and pickling look modules up here
    spec.loader.exec_module(module)
    code = module.main(["--out", str(out_dir)])
    if code != 0:
        raise RuntimeError(f"{gen.script.name} exited with code {code}")


def regenerate_all(out_dir: Path, generators: tuple[Generator, ...]) -> None:
    for gen in generators:
        print(f"== running {gen.script.relative_to(ROOT)} --out {out_dir}")
        run_generator(gen, out_dir)


def check(docs_dir: Path, readme_path: Path, regenerate: Callable[[Path], None], reference: bool = False,
          generators: tuple[Generator, ...] = CHECK_GENERATORS) -> int:
    """Run every check and return the exit code. regenerate(tmp_dir) must write tmp_dir/metrics.json."""
    try:
        committed = load_metrics(docs_dir / "metrics.json")
        claims = load_claims(docs_dir / "claims.toml")
    except ConfigError as err:
        print(f"config error: {err}")
        return EXIT_CONFIG
    unknown = [c.id for c in claims if c.metric not in committed]
    if unknown:
        print(f"config error: claims point at metrics missing from metrics.json: {', '.join(unknown)}")
        return EXIT_CONFIG

    with tempfile.TemporaryDirectory(prefix="quantforge-reproduce-") as tmp:
        fresh_dir = Path(tmp)
        regenerate(fresh_dir)
        try:
            fresh = load_metrics(fresh_dir / "metrics.json")
        except ConfigError as err:
            print(f"config error in the regenerated output: {err}")
            return EXIT_CONFIG
        drift = compare_metrics(committed, fresh, claims)
        claim_problems = check_claims(claims, committed, readme_path.read_text(encoding="utf-8"))
        report_problems = compare_reports(docs_dir, fresh_dir, generators) if reference else []

    for label, problems in (("metric drift", drift), ("claim", claim_problems), ("report", report_problems)):
        for p in problems:
            print(f"{label}: {p}")
    if drift:
        return EXIT_DRIFT
    if claim_problems:
        return EXIT_CLAIM
    if report_problems:
        return EXIT_REFERENCE
    print(f"ok: {len(committed)} metrics and {len(claims)} claims reproduce")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate or check the published numbers.")
    ap.add_argument("--check", action="store_true", help="regenerate into a temporary folder and compare")
    ap.add_argument("--reference", action="store_true",
                    help="with --check, also require byte equal Markdown reports (reference CI job only)")
    args = ap.parse_args(argv)
    if args.reference and not args.check:
        ap.error("--reference needs --check")
    if args.check:
        return check(DOCS, README, lambda out: regenerate_all(out, CHECK_GENERATORS), args.reference)
    regenerate_all(DOCS, ALL_GENERATORS)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
