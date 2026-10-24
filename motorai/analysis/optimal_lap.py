"""Builds the theoretical optimal lap by stitching together the fastest
segment duration seen, bin by bin, across every valid lap in a session.

This is the classic "theoretical best lap" technique (as in MoTeC i2 /
VBox delta tools): for each small distance bin, take whichever lap
traversed it fastest, and sum those best segment times. It is deliberately
NOT "take the minimum cumulative time at each bin", which would let an
early lead on one lap mask a loss on another.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OptimalLap:
    position: np.ndarray        # bin centers, shape (n_bins,)
    segment_ms: np.ndarray      # best-seen duration of each bin, shape (n_bins,)
    cumulative_ms: np.ndarray   # cumulative time to reach end of each bin
    theoretical_best_ms: float
    source_lap_number: np.ndarray  # which lap (index into `laps`) contributed each bin's best segment


def build_optimal_lap(resampled_valid_laps: list[pd.DataFrame], lap_numbers: list[int]) -> OptimalLap:
    if not resampled_valid_laps:
        raise ValueError("need at least one valid lap to build an optimal lap")
    if len(resampled_valid_laps) != len(lap_numbers):
        raise ValueError("resampled_valid_laps and lap_numbers must be the same length")

    n_bins = len(resampled_valid_laps[0])
    time_matrix = np.stack([df["time_ms"].to_numpy() for df in resampled_valid_laps])  # (n_laps, n_bins)

    # Segment duration of bin i = time to go from bin i-1 to bin i; bin 0's
    # "segment" is the time from the start/finish line to the first bin.
    seg_matrix = np.diff(time_matrix, axis=1, prepend=0.0)
    seg_matrix = np.clip(seg_matrix, a_min=0.0, a_max=None)

    best_lap_idx = np.argmin(seg_matrix, axis=0)
    segment_ms = seg_matrix[best_lap_idx, np.arange(n_bins)]
    cumulative_ms = np.cumsum(segment_ms)

    return OptimalLap(
        position=resampled_valid_laps[0]["position"].to_numpy(),
        segment_ms=segment_ms,
        cumulative_ms=cumulative_ms,
        theoretical_best_ms=float(cumulative_ms[-1]),
        source_lap_number=np.array(lap_numbers)[best_lap_idx],
    )


def delta_trace_ms(lap: pd.DataFrame, optimal: OptimalLap) -> np.ndarray:
    """Per-bin (lap time so far) - (theoretical best time so far).

    Rising = losing time in that stretch of track; flat = matching the
    theoretical best; falling would mean beating it (only possible for the
    lap(s) that contributed to the optimal in that bin).
    """
    return lap["time_ms"].to_numpy() - optimal.cumulative_ms
