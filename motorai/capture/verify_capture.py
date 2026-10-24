"""One-off calibration check — run this BEFORE trusting recorded sessions.

Prints live values every ~0.5s. Compare them by eye against the in-game
HUD/dashboard while driving a lap: speed, gear and RPM should match within
rounding, throttle/brake should move 0->1 as you press pedals, and
normalized position should climb 0->1 once per lap then jump back to ~0.

If any field looks shifted or nonsensical (e.g. speed showing thousands,
gear stuck at a huge number), the struct layout in structures.py has
drifted from the installed AC version's SDK — check Documents/Assetto
Corsa/apps/python/*/sim_info.py (ships with the game) against structures.py
and fix the field order/types there first.

    python -m motorai.capture.verify_capture
"""
from __future__ import annotations

import time

from motorai.capture.reader import SharedMemoryReader
from motorai.console_guard import run_with_pause


def main() -> None:
    with SharedMemoryReader() as reader:
        static = reader.static_info
        print(f"track={static.track!r} car={static.carModel!r} player={static.playerName!r}")
        print("Ctrl+C to stop.\n")
        try:
            while True:
                s = reader.poll()
                print(
                    f"pos={s.normalized_car_position:5.3f} "
                    f"speed={s.speed_kmh:6.1f}km/h "
                    f"gear={s.gear:2d} rpm={s.rpms:5d} "
                    f"gas={s.gas:.2f} brake={s.brake:.2f} steer={s.steer_angle:+.2f} "
                    f"lap={s.completed_laps} inPit={s.is_in_pit} tyresOut={s.tyres_out}"
                )
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    run_with_pause(main)
