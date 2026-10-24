"""Detects corners generically from the driven path's curvature, so the
analysis works on any track without a hand-maintained corner database.

Curvature is computed from (car_x, car_z) — the horizontal plane in AC's
coordinate system (Y is elevation) — on the fastest valid lap, since that's
a single coherent drive rather than a stitched-together one.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Corner:
    index: int          # 1-based, in track order
    start_bin: int
    apex_bin: int
    end_bin: int


def _curvature(car_x: np.ndarray, car_z: np.ndarray, smoothing_window: int = 9) -> np.ndarray:
    dx = np.gradient(car_x)
    dz = np.gradient(car_z)
    heading = np.unwrap(np.arctan2(dz, dx))
    dheading = np.gradient(heading)
    curvature = np.abs(dheading)

    kernel = np.ones(smoothing_window) / smoothing_window
    return np.convolve(curvature, kernel, mode="same")


def detect_corners(
    reference_lap: pd.DataFrame,
    curvature_percentile: float = 65.0,
    min_region_bins: int = 4,
    merge_gap_bins: int = 3,
) -> list[Corner]:
    """``reference_lap`` is a resampled lap DataFrame (see resample.py) for
    the fastest valid lap of the session — used purely for track geometry
    and apex speed, not as the time baseline (that's the optimal lap).
    """
    curvature = _curvature(reference_lap["car_x"].to_numpy(), reference_lap["car_z"].to_numpy())
    threshold = np.percentile(curvature, curvature_percentile)
    in_corner = curvature > threshold

    regions = _group_regions(in_corner, merge_gap_bins=merge_gap_bins, min_region_bins=min_region_bins)

    speed = reference_lap["speed_kmh"].to_numpy()
    corners = []
    for i, (start, end) in enumerate(regions, start=1):
        apex = start + int(np.argmin(speed[start : end + 1]))
        corners.append(Corner(index=i, start_bin=start, apex_bin=apex, end_bin=end))
    return corners


def _group_regions(mask: np.ndarray, merge_gap_bins: int, min_region_bins: int) -> list[tuple[int, int]]:
    n = len(mask)
    raw_regions: list[list[int]] = []
    i = 0
    while i < n:
        if mask[i]:
            start = i
            while i < n and mask[i]:
                i += 1
            raw_regions.append([start, i - 1])
        else:
            i += 1

    merged: list[list[int]] = []
    for region in raw_regions:
        if merged and region[0] - merged[-1][1] <= merge_gap_bins:
            merged[-1][1] = region[1]
        else:
            merged.append(region)

    return [(s, e) for s, e in merged if (e - s + 1) >= min_region_bins]
