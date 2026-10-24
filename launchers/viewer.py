"""PyInstaller entry point for MotorAI.exe (the session viewer). See
calibrate.py in this same folder for why imports are deferred and this
lives outside motorai/.

This is a windowed (no console) build, so there's no console to print a
traceback to if something goes wrong before Qt even starts (e.g. a
packaging/import failure) — motorai.ui.app already shows a QMessageBox for
errors that happen *after* Qt is up, but a failure in the import itself
would otherwise just vanish with zero feedback. The except branch below
falls back to a native Windows message box via ctypes (no PySide6 needed)
so that case is visible too.
"""
import traceback


def _main() -> None:
    from motorai.ui.app import main

    main()


if __name__ == "__main__":
    try:
        _main()
    except BaseException:
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, traceback.format_exc(), "MotorAI — ошибка запуска", 0x10)
        except Exception:
            pass
        raise
