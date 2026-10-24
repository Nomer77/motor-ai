from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from motorai.analysis.summary import SessionReport, analyse_session
from motorai.storage.session_store import LapInfo
from motorai.ui.widgets.corner_table_widget import CornerTableWidget
from motorai.ui.widgets.telemetry_chart_widget import TelemetryChartWidget
from motorai.ui.widgets.track_map_widget import TrackMapWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        track: str,
        car: str,
        laps: list[LapInfo],
        frames: dict,
        track_length_m: float | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("MotorAI — анализ заезда")
        self.resize(1280, 820)

        self._track = track
        self._car = car
        self._laps = laps
        self._frames = frames
        self._track_length_m = track_length_m

        self._summary_label = QLabel()
        self._summary_label.setStyleSheet("font-size: 14px; padding: 8px;")

        self._lap_selector = QComboBox()
        for lap in laps:
            suffix = "" if lap.valid else " (невалидный)"
            self._lap_selector.addItem(f"Круг {lap.lap_number} — {lap.lap_time_ms / 1000:.3f}с{suffix}", lap.lap_number)
        self._lap_selector.currentIndexChanged.connect(self._on_lap_changed)

        self._track_map = TrackMapWidget()
        self._telemetry_chart = TelemetryChartWidget()
        self._corner_table = CornerTableWidget()

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.addWidget(QLabel(f"{track} — {car}"))
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Круг для анализа:"))
        header_layout.addWidget(self._lap_selector)

        charts = QSplitter(Qt.Orientation.Horizontal)
        charts.addWidget(self._track_map)
        charts.addWidget(self._telemetry_chart)
        charts.setSizes([420, 860])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(header)
        layout.addWidget(self._summary_label)
        layout.addWidget(charts, stretch=3)
        layout.addWidget(self._corner_table, stretch=2)
        self.setCentralWidget(central)

        self._on_lap_changed(0)

    def _on_lap_changed(self, _index: int) -> None:
        lap_number = self._lap_selector.currentData()
        report = analyse_session(
            self._track,
            self._car,
            self._laps,
            self._frames,
            analysed_lap_number=lap_number,
            track_length_m=self._track_length_m,
        )
        self._render_report(report)

    def _render_report(self, report: SessionReport) -> None:
        self._summary_label.setText(
            f"Круг {report.analysed_lap_number}: {report.analysed_lap_time_ms / 1000:.3f}с  •  "
            f"Теоретический идеал: {report.theoretical_best_ms / 1000:.3f}с  •  "
            f"Отставание: {report.gap_to_theoretical_ms / 1000:+.3f}с  "
            f"(эталонный круг — №{report.reference_lap_number})"
        )

        analysed_lap = report.resampled_laps[report.analysed_lap_number]
        reference_lap = report.resampled_laps[report.reference_lap_number]
        delta = report.delta_trace_ms.to_numpy()
        delta_rate = np.gradient(delta)

        corner_markers = [(c.index, analysed_lap["position"].iloc[c.apex_bin]) for c in report.corners]

        self._track_map.set_data(analysed_lap["car_x"].to_numpy(), analysed_lap["car_z"].to_numpy(), delta_rate)
        self._telemetry_chart.set_data(analysed_lap, reference_lap, delta, corner_markers)
        self._corner_table.set_tips(report.tips)
