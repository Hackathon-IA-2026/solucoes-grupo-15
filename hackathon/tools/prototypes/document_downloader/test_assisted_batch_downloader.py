"""Regression tests for the assisted batch downloader wizard."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))

import assisted_batch_downloader as downloader


class SavedPageValidationTests(unittest.TestCase):
    def test_missing_results_page_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_page = Path(directory) / "resultados.html"

            with self.assertRaisesRegex(SystemExit, "pagina de resultados"):
                downloader.require_saved_file(missing_page, "pagina de resultados")


if __name__ == "__main__":
    unittest.main()
