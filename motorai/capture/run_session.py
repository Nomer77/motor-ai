"""Windows entry point: record a live AC session to disk.

Run this while Assetto Corsa is open and a Practice/Hotlap/Time Attack
session has started (not just sitting in the pit menu). Stop with Ctrl+C
when you're done driving; each completed lap is saved as you go, so an
interrupt never loses more than the lap in progress.

    python -m motorai.capture.run_session
"""
from __future__ import annotations

from motorai.capture.reader import SharedMemoryReader
from motorai.capture.recorder import RecordedLap, SessionRecorder
from motorai.console_guard import run_with_pause
from motorai.storage.session_store import SessionStore


def main() -> None:
    probe = SharedMemoryReader()
    probe.open()
    static = probe.static_info
    track, car, track_length_m = static.track, static.carModel, float(static.trackSPlineLength)
    probe.close()

    store = SessionStore()
    session_dir = store.new_session_dir(track=track, car=car, track_length_m=track_length_m)
    print(f"Recording session: track={track!r} car={car!r}")
    print(f"Saving to: {session_dir}")

    lap_counter = {"n": 0}

    def on_lap_complete(lap: RecordedLap) -> None:
        lap_counter["n"] += 1
        n = lap_counter["n"]
        store.save_lap(
            session_dir,
            lap_number=n,
            lap_time_ms=lap.lap_time_ms,
            valid=lap.valid,
            rows=[vars(s) for s in lap.samples],
        )
        status = "valid" if lap.valid else "INVALID (off-track or pit)"
        print(f"Lap {n}: {lap.lap_time_ms / 1000:.3f}s — {status} — {len(lap.samples)} samples")

    recorder = SessionRecorder(on_lap_complete=on_lap_complete, poll_hz=50)
    try:
        recorder.run_forever()
    except KeyboardInterrupt:
        print("\nStopped. Session saved at:", session_dir)


if __name__ == "__main__":
    run_with_pause(main)
