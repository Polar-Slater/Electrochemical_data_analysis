"""Run this file in VS Code, or use Open EIS Analysis.bat."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT.parent / ".venv-deareis" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            if Path(sys.executable).resolve() != candidate.resolve():
                return subprocess.call([str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]])
            break
    missing = [name for name in ("dearpygui", "pyimpspec", "cvxopt")
               if importlib.util.find_spec(name) is None]
    if missing:
        print("Missing dependencies: " + ", ".join(missing))
        print("Run Setup.bat once, then open launch.py again.")
        return 1
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "src"))
    from deareis.program import main as run
    run()
    return 0


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    raise SystemExit(main())
