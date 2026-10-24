"""Synthetic track + laps generator.

Lets us develop and unit-test the whole analysis/UI pipeline without
Windows or a copy of Assetto Corsa: builds a toy track geometry (straights
+ arcs), derives a physically-plausible "ideal" speed profile from its
curvature, and generates several laps around it — most clean, one or two
with a deliberately injected mistake in a specific corner (braking too
early/hard and carrying less apex speed) so the tip generator has
something real to find.

Output shape mirrors what ``SessionStore.load_session`` returns, so this
can feed straight into ``motorai.analysis.summary.analyse_session``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from motorai.storage.session_store import LapInfo

STEP_M = 0.5  # fine-grid spacing used both for geometry and as the "raw" sample spacing

# (kind, length_or_radius_m, angle_deg, direction) — direction +1 = left/CCW, -1 = right/CW
TRACK_SEGMENTS = [
    ("straight", 300, None, None),
    ("arc", 40, 90, 1),
    ("straight", 150, None, None),
    ("arc", 25, 120, -1),
    ("straight", 200, None, None),
    ("arc", 60, 60, 1),
    ("straight", 250, None, None),
    ("arc", 35, 100, 1),
    ("straight", 180, None, None),
    ("arc", 50, 90, -1),
]

TOP_SPEED_KMH = 240.0
LATERAL_G_LIMIT = 1.6  # tyre grip assumption
BRAKE_SMOOTH_WINDOW_M = 60.0  # how far ahead of a corner the car starts slowing


@dataclass(frozen=True)
class TrackGeometry:
    s: np.ndarray             # normalized position [0,1)
    car_x: np.ndarray
    car_z: np.ndarray
    curvature_signed: np.ndarray
    total_length_m: float


def build_track_geometry(step_m: float = STEP_M) -> TrackGeometry:
    xs, zs, curvatures = [0.0], [0.0], [0.0]
    heading = 0.0
    x, z = 0.0, 0.0

    for kind, a, angle_deg, direction in TRACK_SEGMENTS:
        if kind == "straight":
            n_steps = max(int(a / step_m), 1)
            for _ in range(n_steps):
                x += step_m * math.cos(heading)
                z += step_m * math.sin(heading)
                xs.append(x)
                zs.append(z)
                curvatures.append(0.0)
        else:  # arc
            radius = a
            arc_len = radius * math.radians(angle_deg)
            n_steps = max(int(arc_len / step_m), 1)
            dtheta = math.radians(angle_deg) / n_steps * direction
            for _ in range(n_steps):
                heading += dtheta
                x += step_m * math.cos(heading)
                z += step_m * math.sin(heading)
                xs.append(x)
                zs.append(z)
                curvatures.append(direction / radius)

    car_x = np.array(xs[:-1])
    car_z = np.array(zs[:-1])
    curvature_signed = np.array(curvatures[:-1])
    n = len(car_x)
    total_length_m = n * step_m
    s = np.arange(n) / n

    return TrackGeometry(s=s, car_x=car_x, car_z=car_z, curvature_signed=curvature_signed, total_length_m=total_length_m)


def _ideal_speed_profile(geo: TrackGeometry) -> np.ndarray:
    a_lat_max = LATERAL_G_LIMIT * 9.81
    curvature_abs = np.abs(geo.curvature_signed)
    with np.errstate(divide="ignore"):
        v_curve = np.where(curvature_abs > 1e-6, np.sqrt(a_lat_max / np.maximum(curvature_abs, 1e-6)), np.inf)
    top_speed_ms = TOP_SPEED_KMH / 3.6
    v_curve = np.minimum(v_curve, top_speed_ms)

    window_bins = max(int(BRAKE_SMOOTH_WINDOW_M / STEP_M), 1)
    kernel = np.ones(window_bins) / window_bins
    padded = np.pad(v_curve, window_bins, mode="wrap")
    smoothed = np.convolve(padded, kernel, mode="same")[window_bins:-window_bins]
    return np.minimum(smoothed, v_curve * 1.15)  # smoothing shouldn't let speed exceed the local limit by much


def generate_lap(
    geo: TrackGeometry,
    ideal_speed_ms: np.ndarray,
    rng: np.random.Generator,
    mistake_apex_s: float | None = None,
    mistake_speed_scale: float = 1.0,
    mistake_shift_m: float = 0.0,
    mistake_half_width_m: float = 80.0,
    mistake_lateral_offset_m: float = 0.0,
) -> tuple[pd.DataFrame, float]:
    n = len(geo.s)
    noise = 1.0 + rng.normal(0, 0.01, size=n)
    speed_ms = ideal_speed_ms * noise

    car_x, car_z = geo.car_x, geo.car_z
    if mistake_apex_s is not None:
        center = mistake_apex_s * geo.total_length_m + mistake_shift_m
        dist_m = np.minimum(
            np.abs(geo.s * geo.total_length_m - center),
            geo.total_length_m - np.abs(geo.s * geo.total_length_m - center),
        )
        affected = dist_m < mistake_half_width_m
        speed_ms = np.where(affected, speed_ms * mistake_speed_scale, speed_ms)

        if mistake_lateral_offset_m:
            # Missed-apex simulation: push the driven line sideways (relative
            # to the track's own tangent/normal) near the mistake, tapering
            # to zero at the edges of the affected window.
            bump = np.clip(1.0 - dist_m / mistake_half_width_m, 0.0, 1.0)
            tangent_x, tangent_z = np.gradient(geo.car_x), np.gradient(geo.car_z)
            tangent_norm = np.hypot(tangent_x, tangent_z)
            tangent_norm[tangent_norm < 1e-9] = 1.0
            normal_x, normal_z = -tangent_z / tangent_norm, tangent_x / tangent_norm
            car_x = geo.car_x + bump * mistake_lateral_offset_m * normal_x
            car_z = geo.car_z + bump * mistake_lateral_offset_m * normal_z

    dv = np.gradient(speed_ms, STEP_M)
    decel_scale = 8.0  # m/s^2 that maps to brake=1.0
    accel_scale = 6.0
    brake = np.clip(np.where(dv < 0, -dv / decel_scale, 0.0), 0.0, 1.0)
    gas = np.clip(np.where(dv >= 0, 0.5 + dv / accel_scale, 0.0), 0.0, 1.0)

    dt_s = STEP_M / np.maximum(speed_ms, 1.0)
    current_lap_time_ms = np.cumsum(dt_s) * 1000.0

    steer_angle = np.clip(geo.curvature_signed * 20.0, -1.0, 1.0)

    return pd.DataFrame(
        {
            "normalized_position": geo.s,
            "current_lap_time_ms": current_lap_time_ms,
            "speed_kmh": speed_ms * 3.6,
            "gas": gas,
            "brake": brake,
            "steer_angle": steer_angle,
            "gear": np.full(n, 4),
            "rpms": np.full(n, 6000),
            "car_x": car_x,
            "car_z": car_z,
        }
    ), float(current_lap_time_ms[-1])


def generate_sample_session(
    n_clean_laps: int = 4,
    n_flawed_laps: int = 2,
    seed: int = 42,
) -> tuple[str, str, float, list[LapInfo], dict[int, pd.DataFrame]]:
    rng = np.random.default_rng(seed)
    geo = build_track_geometry()
    ideal_speed_ms = _ideal_speed_profile(geo)

    # Pick a corner apex (roughly) as the trouble spot: the first arc segment's midpoint.
    mistake_apex_s = 300 / geo.total_length_m + (math.radians(90) * 40 / 2) / geo.total_length_m

    laps: list[LapInfo] = []
    frames: dict[int, pd.DataFrame] = {}
    lap_number = 1

    for _ in range(n_clean_laps):
        df, lap_time_ms = generate_lap(geo, ideal_speed_ms, rng)
        frames[lap_number] = df
        laps.append(LapInfo(lap_number=lap_number, lap_time_ms=round(lap_time_ms), valid=True))
        lap_number += 1

    for _ in range(n_flawed_laps):
        df, lap_time_ms = generate_lap(
            geo,
            ideal_speed_ms,
            rng,
            mistake_apex_s=mistake_apex_s,
            mistake_speed_scale=0.85,
            mistake_shift_m=-15.0,
            mistake_lateral_offset_m=2.5,
        )
        frames[lap_number] = df
        laps.append(LapInfo(lap_number=lap_number, lap_time_ms=round(lap_time_ms), valid=True))
        lap_number += 1

    return "Synthetic Test Circuit", "Synthetic GT3", geo.total_length_m, laps, frames
