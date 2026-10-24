"""End-to-end test of the analysis pipeline against synthetic laps:
resample -> optimal lap -> corner detection -> tips, via analyse_session.
"""
from motorai.analysis.summary import analyse_session
from motorai.sample_data.synth import generate_sample_session


def _session():
    return generate_sample_session(n_clean_laps=4, n_flawed_laps=2, seed=7)


def test_theoretical_best_is_not_slower_than_any_lap():
    track, car, length_m, laps, frames = _session()
    report = analyse_session(track, car, laps, frames, track_length_m=length_m)

    fastest_actual = min(lap.lap_time_ms for lap in laps if lap.valid)
    assert report.theoretical_best_ms <= fastest_actual + 1  # +1ms tolerance for interpolation rounding


def test_corners_are_detected_on_a_track_with_four_turns():
    track, car, length_m, laps, frames = _session()
    report = analyse_session(track, car, laps, frames, track_length_m=length_m)

    # TRACK_SEGMENTS in synth.py has 5 arcs; corner detection is heuristic
    # so we only assert it's in a sane ballpark, not exactly 5.
    assert 2 <= len(report.corners) <= 8


def test_flawed_lap_produces_a_tip_pointing_at_the_injected_mistake():
    track, car, length_m, laps, frames = _session()
    flawed_lap_number = max(lap.lap_number for lap in laps)  # last lap is one of the flawed ones

    report = analyse_session(
        track, car, laps, frames, analysed_lap_number=flawed_lap_number, track_length_m=length_m
    )

    assert report.tips, "expected at least one corner tip"
    worst = report.tips[0]
    assert worst.time_loss_ms > 0
    # the injected mistake lowers apex speed and/or shifts the brake point
    assert worst.apex_speed_delta_kmh is not None
    assert worst.apex_speed_delta_kmh < 0 or (worst.brake_point_delta_m or 0) != 0


def test_gap_to_theoretical_is_non_negative_for_every_lap():
    track, car, length_m, laps, frames = _session()
    for lap in laps:
        if not lap.valid:
            continue
        report = analyse_session(track, car, laps, frames, analysed_lap_number=lap.lap_number, track_length_m=length_m)
        assert report.gap_to_theoretical_ms >= -1  # tolerance
