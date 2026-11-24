"""Project configuration matches decisions 0003, 0004, 0006, 0008 and 0012.

Standard library only (unittest, tomllib, ast), so it runs without NumPy or SciPy.
"""

from __future__ import annotations

import ast
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def package_version() -> str:
    """__version__ from src/quantforge/__init__.py, read without importing the package."""
    tree = ast.parse(read("src/quantforge/__init__.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "__version__" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("__version__ not found")


class PyprojectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pyproject = tomllib.loads(read("pyproject.toml"))
        self.project = self.pyproject["project"]

    def test_python_floor_is_312(self) -> None:  # decision 0003
        self.assertEqual(self.project["requires-python"], ">=3.12")
        self.assertEqual(self.pyproject["tool"]["ruff"]["target-version"], "py312")

    def test_runtime_dependencies_are_numpy_and_scipy_only(self) -> None:  # decision 0004
        names = {re.split(r"[<>=!~ \[]", dep, maxsplit=1)[0] for dep in self.project["dependencies"]}
        self.assertEqual(names, {"numpy", "scipy"})

    def test_matplotlib_lives_in_examples_extra(self) -> None:  # decision 0004
        extras = self.project["optional-dependencies"]
        self.assertTrue(any(d.startswith("matplotlib") for d in extras["examples"]))
        self.assertIn("quantforge[examples]", extras["dev"])
        self.assertFalse(any(d.startswith("matplotlib") for d in extras["dev"]))

    def test_version_is_090_and_matches_package(self) -> None:  # decision 0012
        self.assertEqual(self.project["version"], "0.9.0")
        self.assertEqual(package_version(), self.project["version"])

    def test_changelog_lists_the_version(self) -> None:
        self.assertIn("## 0.9.0", read("CHANGELOG.md"))


class GitignoreTest(unittest.TestCase):
    def test_raw_data_and_local_runs_are_ignored(self) -> None:  # decision 0006, acceptance test A13
        lines = {line.strip() for line in read(".gitignore").splitlines()}
        for rule in ("data/", "local/", "*.zip", "*.csv"):
            self.assertIn(rule, lines)


class WorkflowTest(unittest.TestCase):
    """Text checks on the CI file; there is no YAML parser in the standard library."""

    def setUp(self) -> None:
        self.yml = read(".github/workflows/tests.yml")

    def test_token_is_read_only(self) -> None:  # decision 0009, R20
        self.assertRegex(self.yml, r"(?m)^permissions:\n  contents: read$")

    def test_manual_trigger(self) -> None:  # decision 0010
        self.assertRegex(self.yml, r"(?m)^  workflow_dispatch:")

    def test_python_matrix_matches_the_floor(self) -> None:  # decision 0003, acceptance test A25
        for version in ("3.12", "3.13", "3.14"):
            self.assertIn(f'"{version}"', self.yml)
        for old in ("3.10", "3.11"):
            self.assertNotIn(f'"{old}"', self.yml)

    def test_macos_job_and_exact_runner_images(self) -> None:  # decision 0008, acceptance test A24
        self.assertRegex(self.yml, r"macos-\d+")
        self.assertRegex(self.yml, r"ubuntu-\d+\.\d+")
        self.assertNotIn("-latest", self.yml)

    def test_reproduce_check_runs_in_ci(self) -> None:  # decision 0007, walking skeleton step 7
        self.assertIn("python tools/reproduce.py --check", self.yml)


if __name__ == "__main__":
    unittest.main()
