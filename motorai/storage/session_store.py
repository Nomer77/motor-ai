"""Persists recorded sessions to disk and loads them back for analysis.

Layout on disk, one directory per session::

    <root>/<session_id>/
        meta.json          # track, car, created_at
        laps.json          # [{lap_number, lap_time_ms, valid}, ...]
        lap_0001.parquet    # per-lap telemetry, one row per sample
        lap_0002.parquet
        ...

``session_id`` defaults to ``<track>__<car>__<timestamp>`` so sessions on
the same track/car sort and group naturally in the UI's session list.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DEFAULT_ROOT = Path.home() / "Documents" / "MotorAI" / "sessions"

LAP_COLUMNS = [
    "normalized_position",
    "current_lap_time_ms",
    "speed_kmh",
    "gas",
    "brake",
    "steer_angle",
    "gear",
    "rpms",
    "car_x",
    "car_z",
]


@dataclass(frozen=True)
class SessionMeta:
    track: str
    car: str
    created_at: str
    track_length_m: float | None = None


@dataclass(frozen=True)
class LapInfo:
    lap_number: int
    lap_time_ms: int
    valid: bool


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def new_session_dir(self, track: str, car: str, track_length_m: float | None = None) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        session_id = f"{_slug(track)}__{_slug(car)}__{timestamp}"
        path = self.root / session_id
        path.mkdir(parents=True, exist_ok=False)
        meta = SessionMeta(track=track, car=car, created_at=timestamp, track_length_m=track_length_m)
        (path / "meta.json").write_text(json.dumps(asdict(meta), ensure_ascii=False, indent=2))
        (path / "laps.json").write_text("[]")
        return path

    def save_lap(self, session_dir: Path, lap_number: int, lap_time_ms: int, valid: bool, rows: list[dict]) -> None:
        df = pd.DataFrame(rows, columns=LAP_COLUMNS)
        df.to_parquet(session_dir / f"lap_{lap_number:04d}.parquet", index=False)

        laps_path = session_dir / "laps.json"
        laps = json.loads(laps_path.read_text())
        laps.append(asdict(LapInfo(lap_number=lap_number, lap_time_ms=lap_time_ms, valid=valid)))
        laps_path.write_text(json.dumps(laps, ensure_ascii=False, indent=2))

    def list_sessions(self) -> list[Path]:
        return sorted((p for p in self.root.iterdir() if p.is_dir()), reverse=True)

    def load_session(self, session_dir: Path) -> tuple[SessionMeta, list[LapInfo], dict[int, pd.DataFrame]]:
        meta_raw = json.loads((session_dir / "meta.json").read_text())
        meta = SessionMeta(**meta_raw)
        laps_raw = json.loads((session_dir / "laps.json").read_text())
        laps = [LapInfo(**entry) for entry in laps_raw]
        frames = {
            lap.lap_number: pd.read_parquet(session_dir / f"lap_{lap.lap_number:04d}.parquet")
            for lap in laps
        }
        return meta, laps, frames


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in value.strip()) or "unknown"
