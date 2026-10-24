"""Turns per-corner numbers into Russian-language coaching tips.

All comparisons are: analysed lap vs. the fastest valid lap of the session
(for braking/throttle points, apex speed, and apex line — a real, coherent
reference drive) and vs. the theoretical optimal lap (for the time-loss
number, which is cheat-proof against both laps sharing the same weakness).
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
MIN_NOTABLE_APEX_MISS_M = 1.0


@dataclass(frozen=True)
class CornerTip:
    corner_index: int
    time_loss_ms: float
    apex_position_m: float | None       # distance from start/finish line to the apex
    brake_point_delta_m: float | None   # +later than reference, -earlier
    apex_speed_delta_kmh: float | None  # +faster than reference, -slower
    apex_line_miss_m: float             # lateral distance from the reference lap's line, at the apex
    apex_line_side: str | None          # "левее" / "правее" of the reference line, or None if negligible
    throttle_point_delta_m: float | None  # +later, -earlier
    text: str


def _first_above(arr: np.ndarray, threshold: float, start: int, end: int) -> int | None:
    for i in range(start, end + 1):
        if arr[i] > threshold:
            return i
    return None


def _bin_length_m(n_bins: int, track_length_m: float | None) -> float:
    return (track_length_m / n_bins) if track_length_m else 1.0


def _apex_line_miss(analysed_lap: pd.DataFrame, reference_lap: pd.DataFrame, apex_bin: int) -> tuple[float, str | None]:
    """Signed lateral distance (m) between the analysed lap's position and
    the reference lap's position at the apex, measured perpendicular to the
    reference line's direction of travel there — i.e. did this lap actually
    pass through the same point in space as the fastest lap's apex, or cut
    inside/run wide of it.
    """
    n = len(reference_lap)
    i0, i1 = max(apex_bin - 2, 0), min(apex_bin + 2, n - 1)
    rx, rz = reference_lap["car_x"].to_numpy(), reference_lap["car_z"].to_numpy()
    tangent = np.array([rx[i1] - rx[i0], rz[i1] - rz[i0]])
    norm = np.linalg.norm(tangent)
    if norm < 1e-9:
        return 0.0, None
    tangent /= norm
    normal = np.array([-tangent[1], tangent[0]])  # 90° CCW from the direction of travel

    ax = analysed_lap["car_x"].to_numpy()[apex_bin]
    az = analysed_lap["car_z"].to_numpy()[apex_bin]
    offset = np.array([ax - rx[apex_bin], az - rz[apex_bin]])
    signed = float(np.dot(offset, normal))

    if abs(signed) < MIN_NOTABLE_APEX_MISS_M:
        return abs(signed), None
    return abs(signed), ("левее" if signed > 0 else "правее")


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

        apex_position_m = (
            float(reference_lap["position"].iloc[c.apex_bin] * track_length_m) if track_length_m else None
        )

        actual_brake = _first_above(analysed_lap["brake"].to_numpy(), BRAKE_THRESHOLD, window_start, c.apex_bin)
        ref_brake = _first_above(reference_lap["brake"].to_numpy(), BRAKE_THRESHOLD, window_start, c.apex_bin)
        brake_delta_m = (actual_brake - ref_brake) * bin_len if actual_brake is not None and ref_brake is not None else None

        actual_apex_speed = float(np.min(analysed_lap["speed_kmh"].to_numpy()[c.start_bin : c.end_bin + 1]))
        ref_apex_speed = float(np.min(reference_lap["speed_kmh"].to_numpy()[c.start_bin : c.end_bin + 1]))
        apex_speed_delta = actual_apex_speed - ref_apex_speed

        apex_line_miss_m, apex_line_side = _apex_line_miss(analysed_lap, reference_lap, c.apex_bin)

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
        if apex_line_side is not None:
            parts.append(f"на апексе вы прошли {apex_line_side} линии лучшего круга на {apex_line_miss_m:.1f} м")
        if throttle_delta_m is not None and abs(throttle_delta_m) >= MIN_NOTABLE_DISTANCE_M:
            direction = "позже" if throttle_delta_m > 0 else "раньше"
            parts.append(f"газ открываете на {abs(throttle_delta_m):.0f} {distance_unit} {direction}")

        apex_location = f"{apex_position_m:.0f} {distance_unit} от старта" if apex_position_m is not None else f"{reference_lap['position'].iloc[c.apex_bin] * 100:.0f}% круга"

        if parts:
            text = f"Поворот {c.index} (апекс — {apex_location}): потеря {time_loss:.0f} мс — " + "; ".join(parts) + "."
        else:
            text = (
                f"Поворот {c.index} (апекс — {apex_location}): потеря {time_loss:.0f} мс — "
                "явных отличий от лучшего круга не найдено."
            )

        tips.append(
            CornerTip(
                corner_index=c.index,
                time_loss_ms=time_loss,
                apex_position_m=apex_position_m,
                brake_point_delta_m=brake_delta_m,
                apex_speed_delta_kmh=apex_speed_delta,
                apex_line_miss_m=apex_line_miss_m,
                apex_line_side=apex_line_side,
                throttle_point_delta_m=throttle_delta_m,
                text=text,
            )
        )

    return sorted(tips, key=lambda t: t.time_loss_ms, reverse=True)
