"""Output folder guard and metrics file of examples/report_io.py (decisions 0002, 0006, 0007).

Standard library only, so it runs without NumPy or SciPy.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, rel: str):
    """Import a file that is not in an installed package, by path."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rio = load("report_io_under_test", "examples/report_io.py")


class RunIdTest(unittest.TestCase):
    NOW = datetime(2026, 11, 19, 15, 30, tzinfo=UTC)

    def test_binance_name(self) -> None:
        self.assertEqual(rio.make_run_id("data/BTCUSDT-bookTicker-2024-03-01.zip", self.NOW),
                         "BTCUSDT_2024-03-01_20261119T1530Z")

    def test_other_name_is_made_safe(self) -> None:
        run_id = rio.make_run_id("my file (1).csv", self.NOW)
        self.assertRegex(run_id, r"^[A-Za-z0-9._-]+_20261119T1530Z$")


class ResolveOutDirTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name).resolve()
        self.local = self.base / "local"
        self.docs = self.base / "docs"
        self.local.mkdir()
        self.docs.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def resolve(self, out, real_data, run_id="R1"):
        return rio.resolve_out_dir(out, real_data, run_id, local_root=self.local, docs_root=self.docs)

    def test_simulated_default_is_docs(self) -> None:
        self.assertEqual(self.resolve(None, False), self.docs)

    def test_simulated_may_write_anywhere(self) -> None:
        self.assertEqual(self.resolve(self.base / "elsewhere", False), self.base / "elsewhere")

    def test_real_data_default_is_local_runs(self) -> None:
        self.assertEqual(self.resolve(None, True), self.local / "runs" / "R1")

    def test_real_data_inside_local_is_allowed(self) -> None:
        self.assertEqual(self.resolve(self.local / "mine", True), self.local / "mine")

    def test_real_data_into_docs_is_refused(self) -> None:
        with self.assertRaises(rio.OutputOutsideLocalError):
            self.resolve(self.docs, True)

    def test_dot_dot_escape_is_refused(self) -> None:
        with self.assertRaises(rio.OutputOutsideLocalError):
            self.resolve(self.local / ".." / "docs", True)

    def test_symlink_escape_is_refused(self) -> None:
        link = self.local / "link"
        try:
            os.symlink(self.docs, link)
        except OSError:
            self.skipTest("symlinks not available")
        with self.assertRaises(rio.OutputOutsideLocalError):
            self.resolve(link / "run", True)

    def test_exit_code_constant_is_3(self) -> None:  # docs/design.md section 3.4
        self.assertEqual(rio.EXIT_OUTSIDE_LOCAL, 3)


class WriteMetricsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def read(self) -> dict:
        return json.loads((self.out / "metrics.json").read_text(encoding="utf-8"))

    def test_writes_schema_value_and_format(self) -> None:
        rio.write_metrics(self.out, "showcase", {"bs.atm_call": (10.450583572185565, ".6f")})
        data = self.read()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["metrics"]["bs.atm_call"],
                         {"value": 10.450583572185565, "format": ".6f", "generator": "showcase"})

    def test_keeps_other_generators_and_replaces_own(self) -> None:
        rio.write_metrics(self.out, "alpha", {"alpha.r2": (0.01, ".4f")})
        rio.write_metrics(self.out, "showcase", {"old.metric": (1.0, ".1f")})
        rio.write_metrics(self.out, "showcase", {"bs.atm_call": (10.45, ".6f")})
        self.assertEqual(sorted(self.read()["metrics"]), ["alpha.r2", "bs.atm_call"])

    def test_rejects_non_finite_and_bad_format(self) -> None:
        with self.assertRaises(ValueError):
            rio.write_metrics(self.out, "showcase", {"x": (math.nan, ".3f")})
        with self.assertRaises(ValueError):
            rio.write_metrics(self.out, "showcase", {"x": (1.0, "not a format")})


if __name__ == "__main__":
    unittest.main()
