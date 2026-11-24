"""tools/reproduce.py --check: exit codes 0 to 4 and the committed registries (decision 0007).

Standard library only. The report scripts are replaced by a fake regenerate step, so these
tests run without NumPy, SciPy or matplotlib. The real regeneration runs in the CI reproduce job.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("reproduce_under_test", ROOT / "tools" / "reproduce.py")
rp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rp  # dataclasses look their module up here
spec.loader.exec_module(rp)

ATM = 10.450583572185565  # Black-Scholes call, S=K=100, T=1, r=5%, sigma=20%
README_ROW = "| Black-Scholes ATM call (S=K=100, r=5%, σ=20%) | 10.450584 | 10.450584 | Hull |\n"
CLAIMS = """schema_version = 1

[[claim]]
id = "bs-atm-call"
metric = "bs.atm_call"
readme_text = "| Black-Scholes ATM call (S=K=100, r=5%, σ=20%) | 10.450584 |"
abs_tol = 5e-7
"""


def metrics_json(value: float, metric_id: str = "bs.atm_call", version: int = 1) -> str:
    entry = {"value": value, "format": ".6f", "generator": "showcase"}
    return json.dumps({"schema_version": version, "metrics": {metric_id: entry}})


class CheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.docs = base / "docs"
        self.docs.mkdir()
        self.readme = base / "README.md"
        self.readme.write_text("# t\n\n" + README_ROW, encoding="utf-8")
        (self.docs / "metrics.json").write_text(metrics_json(ATM), encoding="utf-8")
        (self.docs / "claims.toml").write_text(CLAIMS, encoding="utf-8")
        (self.docs / "RESULTS.md").write_text("report\n", encoding="utf-8")
        self.fresh_value = ATM
        self.fresh_metric_id = "bs.atm_call"
        self.fresh_report = "report\n"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def fake_regenerate(self, out: Path) -> None:
        (out / "metrics.json").write_text(metrics_json(self.fresh_value, self.fresh_metric_id), encoding="utf-8")
        (out / "RESULTS.md").write_text(self.fresh_report, encoding="utf-8")

    def run_check(self, reference: bool = False) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = rp.check(self.docs, self.readme, self.fake_regenerate, reference)
        return code, buf.getvalue()

    def test_green_as_is(self) -> None:
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_edited_digit_in_metrics_json_is_drift(self) -> None:  # design section 8 step 5
        (self.docs / "metrics.json").write_text(metrics_json(10.450593572185565), encoding="utf-8")
        self.assertEqual(self.run_check()[0], 1)

    def test_regenerated_value_outside_tolerance_is_drift(self) -> None:
        self.fresh_value = ATM + 1e-6
        self.assertEqual(self.run_check()[0], 1)

    def test_printed_digit_change_inside_tolerance_is_drift(self) -> None:
        self.fresh_value = 10.4505834  # within 5e-7, but prints 10.450583
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("printed value changed", out)

    def test_new_uncommitted_metric_is_drift(self) -> None:
        self.fresh_metric_id = "bs.other"
        self.assertEqual(self.run_check()[0], 1)

    def test_edited_digit_in_readme_is_a_claim_failure(self) -> None:  # design section 8 step 5
        self.readme.write_text(README_ROW.replace("| 10.450584 | 10.450584 |", "| 10.450585 | 10.450584 |"),
                               encoding="utf-8")
        code, out = self.run_check()
        self.assertEqual(code, 2)
        self.assertIn("README.md does not contain", out)

    def test_claim_text_disagreeing_with_metric_is_a_claim_failure(self) -> None:
        claims = CLAIMS.replace("10.450584 |\"", "10.450585 |\"")
        (self.docs / "claims.toml").write_text(claims, encoding="utf-8")
        self.readme.write_text(README_ROW.replace("10.450584 | 10.450584", "10.450585 | 10.450584"), encoding="utf-8")
        self.assertEqual(self.run_check()[0], 2)

    def test_missing_or_bad_registries_exit_3(self) -> None:
        cases = {
            "missing claims": lambda: (self.docs / "claims.toml").unlink(),
            "missing metrics": lambda: (self.docs / "metrics.json").unlink(),
            "bad json": lambda: (self.docs / "metrics.json").write_text("{", encoding="utf-8"),
            "unknown metrics schema": lambda: (self.docs / "metrics.json").write_text(metrics_json(ATM, version=2)),
            "unknown claims schema": lambda: (self.docs / "claims.toml").write_text(
                CLAIMS.replace("schema_version = 1", "schema_version = 9")),
            "two tolerances": lambda: (self.docs / "claims.toml").write_text(CLAIMS + "rel_tol = 1e-9\n"),
            "claim on unknown metric": lambda: (self.docs / "claims.toml").write_text(
                CLAIMS.replace('metric = "bs.atm_call"', 'metric = "bs.nope"')),
        }
        for name, breakit in cases.items():
            with self.subTest(name):
                self.tearDown()  # fresh folder for each case
                self.setUp()
                breakit()
                self.assertEqual(self.run_check()[0], 3)

    def test_reference_mode_needs_byte_equal_reports(self) -> None:
        self.assertEqual(self.run_check(reference=True)[0], 0)
        self.fresh_report = "report with a changed digit\n"
        self.assertEqual(self.run_check(reference=False)[0], 0)
        self.assertEqual(self.run_check(reference=True)[0], 4)


class CommittedRegistryTest(unittest.TestCase):
    """The real docs/metrics.json, docs/claims.toml and README.md agree with each other."""

    def test_committed_files_load(self) -> None:
        metrics = rp.load_metrics(ROOT / "docs" / "metrics.json")
        claims = rp.load_claims(ROOT / "docs" / "claims.toml")
        self.assertIn("bs.atm_call", metrics)
        self.assertTrue(claims)

    def test_every_claim_matches_readme_and_its_metric(self) -> None:
        metrics = rp.load_metrics(ROOT / "docs" / "metrics.json")
        claims = rp.load_claims(ROOT / "docs" / "claims.toml")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(rp.check_claims(claims, metrics, readme), [])

    def test_check_on_real_docs_with_an_edited_readme_digit_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            shutil.copytree(ROOT / "docs", docs, ignore=shutil.ignore_patterns("figures"))
            readme = Path(tmp) / "README.md"
            text = (ROOT / "README.md").read_text(encoding="utf-8")
            readme.write_text(text, encoding="utf-8")

            def copy_committed(out: Path) -> None:  # stands in for a regeneration that reproduces exactly
                shutil.copy(docs / "metrics.json", out / "metrics.json")

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rp.check(docs, readme, copy_committed), 0)
                readme.write_text(text.replace("| 10.450584 | 10.450584 |", "| 10.450585 | 10.450584 |", 1),
                                  encoding="utf-8")
                self.assertEqual(rp.check(docs, readme, copy_committed), 2)

    def test_main_rejects_reference_without_check(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            rp.main(["--reference"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
