"""Reads Assetto Corsa's live telemetry from Windows shared memory.

Only usable on Windows while ``acs.exe`` is running. On other platforms
(or when AC is closed) :meth:`SharedMemoryReader.open` raises
``RuntimeError`` — callers should catch that and fall back to sample data.
"""
from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass

from motorai.capture.structures import SPageFileGraphic, SPageFilePhysics, SPageFileStatic

_MAP_NAMES = {
    "physics": "Local\\acpmf_physics",
    "graphics": "Local\\acpmf_graphics",
    "static": "Local\\acpmf_static",
}


@dataclass(frozen=True)
class Snapshot:
    """One polled sample, flattened to the fields analysis actually needs."""

    packet_id: int
    status: int
    session_type: int
    completed_laps: int
    is_in_pit: bool
    is_in_pit_lane: bool
    normalized_car_position: float
    distance_traveled: float
    last_lap_time_ms: int
    best_lap_time_ms: int
    current_lap_time_ms: int
    speed_kmh: float
    gas: float
    brake: float
    steer_angle: float
    gear: int
    rpms: int
    car_x: float
    car_y: float
    car_z: float
    tyres_out: int


class SharedMemoryReader:
    """Thin wrapper around the three AC memory-mapped files."""

    def __init__(self) -> None:
        self._maps: dict[str, "mmap.mmap"] = {}
        self._physics = SPageFilePhysics()
        self._graphics = SPageFileGraphic()
        self._static = SPageFileStatic()

    def open(self) -> None:
        if platform.system() != "Windows":
            raise RuntimeError(
                "AC shared memory is Windows-only; this platform is "
                f"{platform.system()}. Use sample_data for development."
            )
        import mmap  # local import: mmap's tagname kwarg only exists on Windows

        try:
            self._maps = {
                "physics": mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics), _MAP_NAMES["physics"]),
                "graphics": mmap.mmap(-1, ctypes.sizeof(SPageFileGraphic), _MAP_NAMES["graphics"]),
                "static": mmap.mmap(-1, ctypes.sizeof(SPageFileStatic), _MAP_NAMES["static"]),
            }
        except OSError as exc:
            raise RuntimeError(
                "Could not open AC shared memory. Is Assetto Corsa running "
                "and has a session actually started (not just the main menu)?"
            ) from exc

        # mmap.mmap(-1, size, tagname) on Windows CREATES a fresh, zero-filled
        # mapping if none with that name exists yet — it does not raise just
        # because AC isn't running. Without this check, open() would "succeed"
        # and poll() would silently stream all-zero telemetry forever instead
        # of failing loudly.
        ctypes.memmove(ctypes.addressof(self._static), self._maps["static"], ctypes.sizeof(self._static))
        if not self._static.acVersion and not self._static.track:
            self.close()
            raise RuntimeError(
                "AC shared memory is empty — Assetto Corsa doesn't look like it's "
                "running a session right now (main menu doesn't count; get on track "
                "in Practice/Hotlap/Time Attack first)."
            )

    def close(self) -> None:
        for m in self._maps.values():
            m.close()
        self._maps = {}

    def poll(self) -> Snapshot:
        ctypes.memmove(ctypes.addressof(self._physics), self._maps["physics"], ctypes.sizeof(self._physics))
        ctypes.memmove(ctypes.addressof(self._graphics), self._maps["graphics"], ctypes.sizeof(self._graphics))
        if self._static.track == "":
            ctypes.memmove(ctypes.addressof(self._static), self._maps["static"], ctypes.sizeof(self._static))

        p, g = self._physics, self._graphics
        return Snapshot(
            packet_id=g.packetId,
            status=g.status,
            session_type=g.session,
            completed_laps=g.completedLaps,
            is_in_pit=bool(g.isInPit),
            is_in_pit_lane=bool(g.isInPitLane),
            normalized_car_position=g.normalizedCarPosition,
            distance_traveled=g.distanceTraveled,
            last_lap_time_ms=g.iLastTime,
            best_lap_time_ms=g.iBestTime,
            current_lap_time_ms=g.iCurrentTime,
            speed_kmh=p.speedKmh,
            gas=p.gas,
            brake=p.brake,
            steer_angle=p.steerAngle,
            gear=p.gear,
            rpms=p.rpms,
            car_x=g.carCoordinates[0],
            car_y=g.carCoordinates[1],
            car_z=g.carCoordinates[2],
            tyres_out=p.numberOfTyresOut,
        )

    @property
    def static_info(self) -> SPageFileStatic:
        return self._static

    def __enter__(self) -> "SharedMemoryReader":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
