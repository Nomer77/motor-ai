from motorai.storage.session_store import SessionStore


def test_save_and_load_session_roundtrip(tmp_path):
    store = SessionStore(root=tmp_path)
    session_dir = store.new_session_dir(track="Spa", car="GT3 Car")

    rows = [
        {
            "normalized_position": i / 10,
            "current_lap_time_ms": i * 100,
            "speed_kmh": 200.0,
            "gas": 1.0,
            "brake": 0.0,
            "steer_angle": 0.0,
            "car_x": float(i),
            "car_z": 0.0,
        }
        for i in range(10)
    ]
    store.save_lap(session_dir, lap_number=1, lap_time_ms=90000, valid=True, rows=rows)
    store.save_lap(session_dir, lap_number=2, lap_time_ms=85000, valid=False, rows=rows)

    meta, laps, frames = store.load_session(session_dir)

    assert meta.track == "Spa"
    assert meta.car == "GT3 Car"
    assert [lap.lap_number for lap in laps] == [1, 2]
    assert laps[0].valid is True
    assert laps[1].valid is False
    assert len(frames[1]) == 10


def test_list_sessions_sorted_most_recent_first(tmp_path):
    store = SessionStore(root=tmp_path)
    first = store.new_session_dir(track="Spa", car="Car A")
    second = store.new_session_dir(track="Monza", car="Car B")

    sessions = store.list_sessions()
    assert sessions[0] in (first, second)
    assert len(sessions) == 2
