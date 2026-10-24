from motorai.capture.reader import Snapshot
from motorai.capture.recorder import SessionRecorder
from motorai.capture.structures import AC_LIVE


def _snapshot(position: float, **overrides) -> Snapshot:
    base = dict(
        packet_id=0,
        status=AC_LIVE,
        session_type=0,
        completed_laps=0,
        is_in_pit=False,
        is_in_pit_lane=False,
        normalized_car_position=position,
        distance_traveled=0.0,
        last_lap_time_ms=0,
        best_lap_time_ms=0,
        current_lap_time_ms=int(position * 90000),
        speed_kmh=200.0,
        gas=1.0,
        brake=0.0,
        steer_angle=0.0,
        gear=4,
        rpms=6000,
        car_x=0.0,
        car_y=0.0,
        car_z=0.0,
        tyres_out=0,
    )
    base.update(overrides)
    return Snapshot(**base)


def test_lap_boundary_detected_on_position_wraparound():
    completed = []
    recorder = SessionRecorder(on_lap_complete=completed.append)

    for pos in [0.1, 0.5, 0.9, 0.98]:
        recorder._handle_snapshot(_snapshot(pos))
    # wraps back down past the finish line
    recorder._handle_snapshot(_snapshot(0.02, last_lap_time_ms=91234))

    assert len(completed) == 1
    lap = completed[0]
    assert lap.lap_time_ms == 91234
    assert lap.valid is True
    assert len(lap.samples) == 4  # samples buffered before the wrap


def test_lap_marked_invalid_after_going_off_track():
    completed = []
    recorder = SessionRecorder(on_lap_complete=completed.append)

    recorder._handle_snapshot(_snapshot(0.1))
    recorder._handle_snapshot(_snapshot(0.5, tyres_out=4))  # off track mid-lap
    recorder._handle_snapshot(_snapshot(0.9))
    recorder._handle_snapshot(_snapshot(0.02, last_lap_time_ms=90000))

    assert completed[0].valid is False


def test_samples_while_in_pit_are_not_recorded():
    completed = []
    recorder = SessionRecorder(on_lap_complete=completed.append)

    recorder._handle_snapshot(_snapshot(0.1, is_in_pit=True))
    recorder._handle_snapshot(_snapshot(0.9))
    recorder._handle_snapshot(_snapshot(0.02, last_lap_time_ms=90000))

    assert len(completed[0].samples) == 1
