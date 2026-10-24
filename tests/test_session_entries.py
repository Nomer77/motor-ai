from motorai.storage.session_store import SessionStore
from motorai.ui.session_entries import DEMO_LABEL, build_entries, resolve_initial_index


def _make_session(store, track, car):
    session_dir = store.new_session_dir(track=track, car=car, track_length_m=5000.0)
    rows = [
        {
            "normalized_position": i / 5,
            "current_lap_time_ms": i * 1000,
            "speed_kmh": 200.0,
            "gas": 1.0,
            "brake": 0.0,
            "steer_angle": 0.0,
            "car_x": float(i),
            "car_z": 0.0,
        }
        for i in range(5)
    ]
    store.save_lap(session_dir, lap_number=1, lap_time_ms=90000, valid=True, rows=rows)
    return session_dir


def test_build_entries_lists_recorded_sessions_then_demo(tmp_path):
    store = SessionStore(root=tmp_path)
    first = _make_session(store, "Spa", "Car A")
    second = _make_session(store, "Monza", "Car B")

    entries = build_entries(store)

    assert [e.path for e in entries[:-1]] == sorted([first, second], reverse=True)
    assert entries[-1].label == DEMO_LABEL
    assert entries[-1].path is None


def test_build_entries_includes_extra_session_outside_store_root(tmp_path):
    store = SessionStore(root=tmp_path / "root")
    other_store = SessionStore(root=tmp_path / "elsewhere")
    external = _make_session(other_store, "Nordschleife", "Car C")

    entries = build_entries(store, extra_session=external)

    assert entries[0].path == external
    assert entries[0].loader()[0] == "Nordschleife"


def test_entry_loader_returns_session_data(tmp_path):
    store = SessionStore(root=tmp_path)
    session_dir = _make_session(store, "Spa", "Car A")

    entries = build_entries(store)
    track, car, track_length_m, laps, frames = entries[0].loader()

    assert track == "Spa"
    assert car == "Car A"
    assert track_length_m == 5000.0
    assert len(laps) == 1
    assert 1 in frames
    assert entries[0].path == session_dir


def test_resolve_initial_index_prefers_requested_path(tmp_path):
    store = SessionStore(root=tmp_path)
    first = _make_session(store, "Spa", "Car A")
    _make_session(store, "Monza", "Car B")
    entries = build_entries(store)

    index = resolve_initial_index(entries, requested_path=first, demo_requested=False)
    assert entries[index].path == first


def test_resolve_initial_index_demo_requested(tmp_path):
    store = SessionStore(root=tmp_path)
    _make_session(store, "Spa", "Car A")
    entries = build_entries(store)

    index = resolve_initial_index(entries, requested_path=None, demo_requested=True)
    assert entries[index].path is None


def test_resolve_initial_index_defaults_to_most_recent(tmp_path):
    store = SessionStore(root=tmp_path)
    _make_session(store, "Spa", "Car A")
    entries = build_entries(store)

    index = resolve_initial_index(entries, requested_path=None, demo_requested=False)
    assert index == 0
