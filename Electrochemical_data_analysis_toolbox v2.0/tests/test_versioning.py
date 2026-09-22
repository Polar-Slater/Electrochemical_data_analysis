from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


TOOLBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLBOX))

import electrochemical_toolbox


class VersioningTests(unittest.TestCase):
    def test_version_is_semantic_and_displayed(self) -> None:
        version = (TOOLBOX / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertEqual(electrochemical_toolbox.APP_VERSION, version)
        self.assertIn(f"v{version}", electrochemical_toolbox.APP_TITLE)

    def test_current_version_has_a_changelog_entry(self) -> None:
        version = (TOOLBOX / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
        changelog = (TOOLBOX / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
