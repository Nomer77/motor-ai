import pandas as pd

from motorai.analysis.resample import resample_lap


def test_resample_lap_interpolates_monotonic_signal():
    raw = pd.DataFrame(
        {
            "normalized_position": [0.0, 0.25, 0.5, 0.75, 0.999],
            "current_lap_time_ms": [0, 2500, 5000, 7500, 9990],
            "speed_kmh": [100, 150, 200, 150, 100],
            "gas": [1, 1, 1, 1, 1],
            "brake": [0, 0, 0, 0, 0],
            "steer_angle": [0, 0, 0, 0, 0],
            "car_x": [0, 1, 2, 3, 4],
            "car_z": [0, 0, 0, 0, 0],
        }
    )

    out = resample_lap(raw, n_bins=10)

    assert len(out) == 10
    assert list(out.columns) == ["position", "time_ms", "speed_kmh", "gas", "brake", "steer_angle", "car_x", "car_z"]
    # time should increase monotonically with position, matching the raw trend
    assert (out["time_ms"].diff().dropna() >= 0).all()
    # speed peaks near the middle of the lap, as in the raw signal
    assert out["speed_kmh"].idxmax() in range(3, 7)


def test_resample_lap_dedupes_duplicate_positions():
    raw = pd.DataFrame(
        {
            "normalized_position": [0.1, 0.1, 0.5, 0.9],
            "current_lap_time_ms": [100, 110, 500, 900],
            "speed_kmh": [100, 110, 200, 300],
            "gas": [1, 1, 1, 1],
            "brake": [0, 0, 0, 0],
            "steer_angle": [0, 0, 0, 0],
            "car_x": [0, 0, 1, 2],
            "car_z": [0, 0, 0, 0],
        }
    )

    out = resample_lap(raw, n_bins=5)
    assert len(out) == 5
    assert out["time_ms"].notna().all()
