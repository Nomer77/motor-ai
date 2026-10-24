"""Keeps a double-clicked console .exe window open on error or on normal
exit, so the message is actually readable instead of flashing and closing.
"""
from __future__ import annotations

import sys
import traceback
from typing import Callable


def run_with_pause(main: Callable[[], None]) -> None:
    try:
        main()
    except KeyboardInterrupt:
        raise
    except Exception:
        traceback.print_exc()
    if getattr(sys, "frozen", False):
        input("\nНажми Enter, чтобы закрыть окно...")
