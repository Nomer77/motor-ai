"""PyInstaller entry point for MotorAICalibrate.exe.

Deliberately lives OUTSIDE the motorai/ package (as a sibling of it) and
defers every import of motorai.* to inside the guarded try/except below.
This matters: if this file imported motorai.capture.reader at the top
(module level, before __main__ even runs), any failure there — including
PyInstaller failing to bundle the package correctly — would crash with an
unhandled exception before the error-reporting code ever gets a chance to
run, and the console window closes instantly with nothing visible. Putting
the import inside the try block, in a standalone script outside the
package, avoids both the "can't report the error" problem and the
"PyInstaller gets confused about a script nested inside its own package"
problem that caused it in the first place.
"""
import sys
import traceback


def _main() -> None:
    from motorai.capture.verify_capture import main

    main()


if __name__ == "__main__":
    try:
        _main()
    except BaseException:
        traceback.print_exc()
    input("\nНажми Enter, чтобы закрыть окно...")
