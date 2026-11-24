"""alpha_research.py refuses real data output outside local/ with exit code 3 (decisions 0002, 0006).

Needs the full environment (the script imports quantforge, which needs SciPy). Skipped otherwise;
the guard logic itself is tested without SciPy in test_report_io.py.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE_FULL_ENV = all(importlib.util.find_spec(m) is not None for m in ("scipy", "matplotlib"))


@unittest.skipUnless(HAVE_FULL_ENV, "needs SciPy and matplotlib (uv sync --extra dev)")
class AlphaOutputGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(ROOT / "examples"))
        script = ROOT / "examples" / "alpha_research.py"
        spec = importlib.util.spec_from_file_location("alpha_research_under_test", script)
        cls.alpha = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.alpha
        spec.loader.exec_module(cls.alpha)

    def run_main(self, argv: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return self.alpha.main(argv)

    def test_real_data_into_docs_exits_3_before_reading(self) -> None:
        # The file does not exist: exit 3 proves the guard runs before any data is read.
        before = sorted(p.name for p in (ROOT / "docs").iterdir())
        code = self.run_main(["--bookticker", "missing-BTCUSDT-bookTicker-2024-03-01.zip", "--out", str(ROOT / "docs")])
        self.assertEqual(code, 3)
        self.assertEqual(sorted(p.name for p in (ROOT / "docs").iterdir()), before)

    def test_real_data_into_a_temp_folder_exits_3(self) -> None:
        outside = Path(tempfile.gettempdir()) / "quantforge-not-local"
        code = self.run_main(["--bookticker", "x.csv", "--out", str(outside)])
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
