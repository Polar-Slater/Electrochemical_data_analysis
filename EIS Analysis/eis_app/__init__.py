"""EIS Analysis custom application support (GPL-3.0-or-later)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
APP_TITLE = f"EIS Analysis {VERSION}"


def user_directory(kind):
    return str(ROOT / ".user-data" / kind)
