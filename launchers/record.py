"""PyInstaller entry point for MotorAIRecord.exe. See calibrate.py in this
same folder for why imports are deferred and this lives outside motorai/.
"""
import sys
import traceback


def _main() -> None:
    from motorai.capture.run_session import main

    main()


if __name__ == "__main__":
    try:
        _main()
    except BaseException:
        traceback.print_exc()
    input("\nНажми Enter, чтобы закрыть окно...")
