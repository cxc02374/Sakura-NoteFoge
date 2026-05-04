"""Sakura NoteForge - PyInstaller エントリポイント"""
import sys
from pathlib import Path

# frozen(PyInstaller)環境では sys._MEIPASS にバンドル済み
# 開発環境では src/ をパスに追加して noteforge パッケージを解決する
if not getattr(sys, 'frozen', False):
    _here = Path(__file__).resolve().parent
    _src = _here / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from noteforge.main import run_app  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_app())
