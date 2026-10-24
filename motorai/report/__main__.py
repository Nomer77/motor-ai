"""
    python -m motorai.report --demo --out report.html
    python -m motorai.report --session <path> --lap 3 --out report.html
"""
from __future__ import annotations

import argparse
from pathlib import Path

from motorai.analysis.summary import analyse_session
from motorai.console_guard import run_with_pause
from motorai.report.html_report import generate_html_report
from motorai.sample_data.synth import generate_sample_session
from motorai.storage.session_store import SessionStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--session", type=Path)
    parser.add_argument("--lap", type=int, default=None)
    parser.add_argument("--out", type=Path, default=Path("report.html"))
    args = parser.parse_args()

    if args.demo:
        track, car, track_length_m, laps, frames = generate_sample_session()
    else:
        store = SessionStore()
        session_dir = args.session
        if session_dir is None:
            sessions = store.list_sessions()
            if not sessions:
                print("No recorded sessions found. Record one first with MotorAIRecord, or pass --demo.")
                return
            session_dir = sessions[0]
        meta, laps, frames = store.load_session(session_dir)
        track, car, track_length_m = meta.track, meta.car, meta.track_length_m

    report = analyse_session(track, car, laps, frames, analysed_lap_number=args.lap, track_length_m=track_length_m)
    generate_html_report(report, args.out)
    print(f"Report written to {args.out.resolve()}")


if __name__ == "__main__":
    run_with_pause(main)
