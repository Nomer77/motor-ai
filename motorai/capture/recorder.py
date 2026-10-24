"""Polls AC shared memory and groups samples into per-lap telemetry.

Lap boundaries are detected from ``normalizedCarPosition`` wrapping from
~1.0 back to ~0.0, rather than from ``completedLaps``, because the position
wrap is what we need anyway to align samples spatially — using one signal
for both keeps the state machine simple.

A lap is marked invalid if the car went off track (more than 2 wheels over
track limits at any point) or spent any time in the pit lane during it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from motorai.capture.reader import SharedMemoryReader, Snapshot
from motorai.capture.structures import AC_LIVE

WRAP_THRESHOLD = 0.5  # position jump bigger than this (going down) = new lap


@dataclass
class LapSample:
    normalized_position: float
    current_lap_time_ms: int
    speed_kmh: float
    gas: float
    brake: float
    steer_angle: float
    gear: int
    rpms: int
    car_x: float
    car_z: float


@dataclass
class RecordedLap:
    lap_time_ms: int
    valid: bool
    samples: list[LapSample] = field(default_factory=list)


class SessionRecorder:
    """Drives the polling loop; hands finished laps to ``on_lap_complete``."""

    def __init__(self, on_lap_complete, poll_hz: int = 50) -> None:
        self.on_lap_complete = on_lap_complete
        self.poll_period = 1.0 / poll_hz
        self._reader = SharedMemoryReader()
        self._prev_position: float | None = None
        self._buffer: list[LapSample] = []
        self._went_off_track = False
        self._visited_pit_lane = False
        self._running = False

    def run_forever(self) -> None:
        with self._reader:
            self._running = True
            while self._running:
                snap = self._reader.poll()
                self._handle_snapshot(snap)
                time.sleep(self.poll_period)

    def stop(self) -> None:
        self._running = False

    def _handle_snapshot(self, snap: Snapshot) -> None:
        if snap.status != AC_LIVE:
            return

        if snap.tyres_out > 2:
            self._went_off_track = True
        if snap.is_in_pit_lane:
            self._visited_pit_lane = True

        pos = snap.normalized_car_position
        if self._prev_position is not None and pos < self._prev_position - WRAP_THRESHOLD:
            self._finish_lap(snap.last_lap_time_ms)
        self._prev_position = pos

        if not snap.is_in_pit:
            self._buffer.append(
                LapSample(
                    normalized_position=pos,
                    current_lap_time_ms=snap.current_lap_time_ms,
                    speed_kmh=snap.speed_kmh,
                    gas=snap.gas,
                    brake=snap.brake,
                    steer_angle=snap.steer_angle,
                    gear=snap.gear,
                    rpms=snap.rpms,
                    car_x=snap.car_x,
                    car_z=snap.car_z,
                )
            )

    def _finish_lap(self, lap_time_ms: int) -> None:
        if self._buffer:
            lap = RecordedLap(
                lap_time_ms=lap_time_ms,
                valid=not self._went_off_track and not self._visited_pit_lane,
                samples=self._buffer,
            )
            self.on_lap_complete(lap)
        self._buffer = []
        self._went_off_track = False
        self._visited_pit_lane = False
