"""Desktop entry point.

    python -m motorai.ui.app --demo              # open on the synthetic demo session
    python -m motorai.ui.app --session <path>     # open on a specific recorded session
    python -m motorai.ui.app                      # opens the most recent recorded session

Either way, the session browser in the top bar lets you switch between any
recorded session (and the demo one) without relaunching.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from motorai.storage.session_store import SessionStore
from motorai.ui.main_window import MainWindow
from motorai.ui.session_entries import build_entries, resolve_initial_index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="open on the synthetic demo session")
    parser.add_argument("--session", type=Path, help="path to a specific recorded session directory")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    try:
        store = SessionStore()
        entries = build_entries(store, extra_session=args.session)
        initial_index = resolve_initial_index(entries, requested_path=args.session, demo_requested=args.demo)
        window = MainWindow(entries, initial_index=initial_index)
    except Exception:
        QMessageBox.critical(None, "MotorAI — ошибка", traceback.format_exc())
        sys.exit(1)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
