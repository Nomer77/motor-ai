"""Resamples raw, irregularly-timed telemetry samples onto a fixed grid of
track-distance bins (``normalized_car_position`` in [0, 1)).

Working in distance space rather than time space is what makes laps
comparable turn-by-turn regardless of how fast each lap actually was.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_N_BINS = 400

RESAMPLE_COLUMNS = [
    "speed_kmh",
    "gas",
    "brake",
    "steer_angle",
    "car_x",
    "car_z",
]


def resample_lap(raw: pd.DataFrame, n_bins: int = DEFAULT_N_BINS) -> pd.DataFrame:
    """Interpolate one lap's raw samples onto ``n_bins`` evenly spaced
    position bins covering [0, 1).

    Returns a DataFrame with columns ``position`` plus everything in
    ``RESAMPLE_COLUMNS``, one row per bin, sorted by position.
    """
    clean = (
        raw.sort_values("normalized_position")
        .groupby("normalized_position", as_index=False)
        .mean()
    )
    xp = clean["normalized_position"].to_numpy()

    bin_width = 1.0 / n_bins
    centers = (np.arange(n_bins) + 0.5) * bin_width

    out = {
        "position": centers,
        "time_ms": np.interp(centers, xp, clean["current_lap_time_ms"].to_numpy()),
    }
    for col in RESAMPLE_COLUMNS:
        out[col] = np.interp(centers, xp, clean[col].to_numpy())
    return pd.DataFrame(out)
