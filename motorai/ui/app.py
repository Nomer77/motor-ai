"""Desktop entry point.

    python -m motorai.ui.app --demo              # synthetic session, no AC/Windows needed
    python -m motorai.ui.app --session <path>     # a session recorded by capture.run_session
    python -m motorai.ui.app                      # opens the most recent recorded session
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from motorai.sample_data.synth import generate_sample_session
from motorai.storage.session_store import SessionStore
from motorai.ui.main_window import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="load a synthetic session instead of recorded data")
    parser.add_argument("--session", type=Path, help="path to a specific recorded session directory")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    try:
        if args.demo:
            track, car, track_length_m, laps, frames = generate_sample_session()
        else:
            store = SessionStore()
            session_dir = args.session
            if session_dir is None:
                sessions = store.list_sessions()
                if not sessions:
                    QMessageBox.warning(
                        None,
                        "MotorAI",
                        "Записанных сессий пока нет.\n\n"
                        "Сначала запиши заезд через MotorAIRecord.exe (во время сессии в AC),\n"
                        "либо открой демо-данные: MotorAI.exe --demo",
                    )
                    sys.exit(1)
                session_dir = sessions[0]
            meta, laps, frames = store.load_session(session_dir)
            track, car, track_length_m = meta.track, meta.car, None

        window = MainWindow(track, car, laps, frames, track_length_m=track_length_m)
    except SystemExit:
        raise
    except Exception:
        QMessageBox.critical(None, "MotorAI — ошибка", traceback.format_exc())
        sys.exit(1)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
