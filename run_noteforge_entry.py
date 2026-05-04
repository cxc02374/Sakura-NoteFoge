"""Sakura NoteForge - PyInstaller エントリポイント"""
import sys
from pathlib import Path

# assets を同梱パスから解決できるように sys.path を調整
_here = Path(__file__).resolve().parent
_src = _here / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from noteforge.main import run_app  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_app())
