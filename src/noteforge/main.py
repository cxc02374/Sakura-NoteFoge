from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from .app import NoteForgeWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Sakura NoteForge")
    app.setOrganizationName("Sakura")

    win = NoteForgeWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
