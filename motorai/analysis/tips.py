"""Turns per-corner numbers into Russian-language coaching tips.

All comparisons are: analysed lap vs. the fastest valid lap of the session
(for braking/throttle points and apex speed — a real, coherent reference
drive) and vs. the theoretical optimal lap (for the time-loss number,
which is cheat-proof against both laps sharing the same weakness).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from motorai.analysis.corners import Corner
from motorai.analysis.optimal_lap import OptimalLap

BRAKE_THRESHOLD = 0.1
THROTTLE_THRESHOLD = 0.8
MIN_NOTABLE_DISTANCE_M = 2.0
MIN_NOTABLE_SPEED_KMH = 1.5


@dataclass(frozen=True)
class CornerTip:
    corner_index: int
    time_loss_ms: float
    brake_point_delta_m: float | None   # +later than reference, -earlier
    apex_speed_delta_kmh: float | None  # +faster than reference, -slower
    throttle_point_delta_m: float | None  # +later, -earlier
    text: str


def _first_above(arr: np.ndarray, threshold: float, start: int, end: int) -> int | None:
    for i in range(start, end + 1):
        if arr[i] > threshold:
            return i
    return None


def _bin_length_m(n_bins: int, track_length_m: float | None) -> float:
    return (track_length_m / n_bins) if track_length_m else 1.0


def build_corner_tips(
    analysed_lap: pd.DataFrame,
    reference_lap: pd.DataFrame,
    optimal: OptimalLap,
    corners: list[Corner],
    track_length_m: float | None = None,
) -> list[CornerTip]:
    n_bins = len(analysed_lap)
    bin_len = _bin_length_m(n_bins, track_length_m)
    distance_unit = "м" if track_length_m else "усл.ед."

    delta = analysed_lap["time_ms"].to_numpy() - optimal.cumulative_ms

    tips = []
    for c in corners:
        window_start = max(c.start_bin - 10, 0)

        time_loss = float(delta[c.end_bin] - delta[max(c.start_bin - 1, 0)])

        actual_brake = _first_above(analysed_lap["brake"].to_numpy(), BRAKE_THRESHOLD, window_start, c.apex_bin)
        ref_brake = _first_above(reference_lap["brake"].to_numpy(), BRAKE_THRESHOLD, window_start, c.apex_bin)
        brake_delta_m = (actual_brake - ref_brake) * bin_len if actual_brake is not None and ref_brake is not None else None

        actual_apex_speed = float(np.min(analysed_lap["speed_kmh"].to_numpy()[c.start_bin : c.end_bin + 1]))
        ref_apex_speed = float(np.min(reference_lap["speed_kmh"].to_numpy()[c.start_bin : c.end_bin + 1]))
        apex_speed_delta = actual_apex_speed - ref_apex_speed

        actual_throttle = _first_above(analysed_lap["gas"].to_numpy(), THROTTLE_THRESHOLD, c.apex_bin, c.end_bin)
        ref_throttle = _first_above(reference_lap["gas"].to_numpy(), THROTTLE_THRESHOLD, c.apex_bin, c.end_bin)
        throttle_delta_m = (actual_throttle - ref_throttle) * bin_len if actual_throttle is not None and ref_throttle is not None else None

        parts = []
        if brake_delta_m is not None and abs(brake_delta_m) >= MIN_NOTABLE_DISTANCE_M:
            direction = "позже" if brake_delta_m > 0 else "раньше"
            parts.append(f"тормозите на {abs(brake_delta_m):.0f} {distance_unit} {direction}, чем в лучшем круге")
        if abs(apex_speed_delta) >= MIN_NOTABLE_SPEED_KMH:
            if apex_speed_delta < 0:
                parts.append(f"скорость в апексе ниже на {abs(apex_speed_delta):.1f} км/ч")
            else:
                parts.append(f"скорость в апексе выше на {apex_speed_delta:.1f} км/ч")
        if throttle_delta_m is not None and abs(throttle_delta_m) >= MIN_NOTABLE_DISTANCE_M:
            direction = "позже" if throttle_delta_m > 0 else "раньше"
            parts.append(f"газ открываете на {abs(throttle_delta_m):.0f} {distance_unit} {direction}")

        if parts:
            text = f"Поворот {c.index}: потеря {time_loss:.0f} мс — " + "; ".join(parts) + "."
        else:
            text = f"Поворот {c.index}: потеря {time_loss:.0f} мс — явных отличий от лучшего круга не найдено."

        tips.append(
            CornerTip(
                corner_index=c.index,
                time_loss_ms=time_loss,
                brake_point_delta_m=brake_delta_m,
                apex_speed_delta_kmh=apex_speed_delta,
                throttle_point_delta_m=throttle_delta_m,
                text=text,
            )
        )

    return sorted(tips, key=lambda t: t.time_loss_ms, reverse=True)
