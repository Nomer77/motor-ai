"""Builds the list shown by the UI's session browser, and picks which one
opens initially. Pure Python, no Qt — so this is unit-testable without a
display, unlike the widgets that consume it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from motorai.sample_data.synth import generate_sample_session
from motorai.storage.session_store import LapInfo, SessionStore

LoaderResult = tuple[str, str, float | None, list[LapInfo], dict[int, pd.DataFrame]]

DEMO_LABEL = "Демо (синтетические данные)"


@dataclass(frozen=True)
class SessionEntry:
    label: str
    loader: Callable[[], LoaderResult]
    path: Path | None  # None for the synthetic demo entry


def build_entries(store: SessionStore, extra_session: Path | None = None) -> list[SessionEntry]:
    """``extra_session`` guarantees that path is present in the list even
    if it's outside ``store.root`` (covers ``--session <arbitrary path>``).
    """
    session_dirs = list(store.list_sessions())
    if extra_session is not None and extra_session not in session_dirs:
        session_dirs.insert(0, extra_session)

    entries = []
    for session_dir in session_dirs:
        try:
            meta, _, _ = store.load_session(session_dir)
        except (OSError, ValueError, KeyError):
            continue  # skip partially-written or corrupted session directories
        label = f"{meta.track} — {meta.car} — {_format_timestamp(meta.created_at)}"
        entries.append(SessionEntry(label=label, loader=_recorded_loader(store, session_dir), path=session_dir))

    entries.append(SessionEntry(label=DEMO_LABEL, loader=generate_sample_session, path=None))
    return entries


def resolve_initial_index(entries: list[SessionEntry], requested_path: Path | None, demo_requested: bool) -> int:
    if requested_path is not None:
        for i, entry in enumerate(entries):
            if entry.path == requested_path:
                return i
    if demo_requested:
        for i, entry in enumerate(entries):
            if entry.path is None:
                return i
    return 0


def _recorded_loader(store: SessionStore, session_dir: Path) -> Callable[[], LoaderResult]:
    def load() -> LoaderResult:
        meta, laps, frames = store.load_session(session_dir)
        return meta.track, meta.car, meta.track_length_m, laps, frames

    return load


def _format_timestamp(raw: str) -> str:
    try:
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw
