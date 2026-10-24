"""Top-level entry point for turning a loaded session into a report model:
resample every lap, build the theoretical optimal lap, detect corners on
the fastest valid lap, and generate tips for whichever lap you want to
review (defaults to the fastest valid one).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from motorai.analysis.corners import Corner, detect_corners
from motorai.analysis.optimal_lap import OptimalLap, build_optimal_lap, delta_trace_ms
from motorai.analysis.resample import DEFAULT_N_BINS, resample_lap
from motorai.analysis.tips import CornerTip, build_corner_tips
from motorai.storage.session_store import LapInfo


@dataclass(frozen=True)
class SessionReport:
    track: str
    car: str
    analysed_lap_number: int
    analysed_lap_time_ms: int
    theoretical_best_ms: float
    gap_to_theoretical_ms: float
    reference_lap_number: int
    optimal: OptimalLap
    corners: list[Corner]
    resampled_laps: dict[int, pd.DataFrame]
    delta_trace_ms: "pd.Series"
    tips: list[CornerTip]


def analyse_session(
    track: str,
    car: str,
    laps: list[LapInfo],
    frames: dict[int, pd.DataFrame],
    analysed_lap_number: int | None = None,
    n_bins: int = DEFAULT_N_BINS,
    track_length_m: float | None = None,
) -> SessionReport:
    valid_laps = [lap for lap in laps if lap.valid and lap.lap_number in frames]
    if not valid_laps:
        raise ValueError("session has no valid laps to analyse")

    resampled = {lap.lap_number: resample_lap(frames[lap.lap_number], n_bins) for lap in valid_laps}

    reference_lap_info = min(valid_laps, key=lambda lap: lap.lap_time_ms)
    reference_lap = resampled[reference_lap_info.lap_number]

    optimal = build_optimal_lap(
        [resampled[lap.lap_number] for lap in valid_laps],
        [lap.lap_number for lap in valid_laps],
    )

    corners = detect_corners(reference_lap)

    target_lap_number = analysed_lap_number or reference_lap_info.lap_number
    analysed_lap = resampled.get(target_lap_number)
    if analysed_lap is None:
        raise ValueError(f"lap {target_lap_number} not found or invalid")

    tips = build_corner_tips(analysed_lap, reference_lap, optimal, corners, track_length_m)
    analysed_lap_time_ms = next(lap.lap_time_ms for lap in laps if lap.lap_number == target_lap_number)

    return SessionReport(
        track=track,
        car=car,
        analysed_lap_number=target_lap_number,
        analysed_lap_time_ms=analysed_lap_time_ms,
        theoretical_best_ms=optimal.theoretical_best_ms,
        gap_to_theoretical_ms=analysed_lap_time_ms - optimal.theoretical_best_ms,
        reference_lap_number=reference_lap_info.lap_number,
        optimal=optimal,
        corners=corners,
        resampled_laps=resampled,
        delta_trace_ms=pd.Series(delta_trace_ms(analysed_lap, optimal), index=analysed_lap["position"]),
        tips=tips,
    )
