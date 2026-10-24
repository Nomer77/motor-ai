"""Speed / throttle+brake / delta-time, analysed lap vs reference lap,
stacked and sharing the x-axis (track position) — never a dual-axis chart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from motorai.ui.palette import (
    COLOR_ANALYSED_LAP,
    COLOR_LOSING_TIME,
    COLOR_REFERENCE_LAP,
    GRID_LINE,
    SURFACE_LIGHT,
    TEXT_SECONDARY,
)


class TelemetryChartWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._figure = Figure(figsize=(7, 6), facecolor=SURFACE_LIGHT)
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)

    def set_data(
        self,
        analysed_lap: pd.DataFrame,
        reference_lap: pd.DataFrame,
        delta_ms: np.ndarray,
        corner_markers: list[tuple[int, float]] | None = None,
    ) -> None:
        self._figure.clear()
        axes = self._figure.subplots(3, 1, sharex=True)
        position = analysed_lap["position"].to_numpy()

        self._plot_series(
            axes[0], position, analysed_lap["speed_kmh"], reference_lap["speed_kmh"], "Скорость, км/ч"
        )
        self._plot_pedals(axes[1], position, analysed_lap)
        self._plot_delta(axes[2], position, delta_ms)

        if corner_markers:
            for ax in axes:
                for _, pos in corner_markers:
                    ax.axvline(pos, color=GRID_LINE, linewidth=1, zorder=0)

        axes[0].legend(loc="lower right", fontsize=8, frameon=False)
        axes[-1].set_xlabel("Позиция на круге", color=TEXT_SECONDARY, fontsize=9)
        self._figure.tight_layout()
        self._canvas.draw()

    def _plot_series(self, ax, position, analysed, reference, ylabel) -> None:
        ax.set_facecolor(SURFACE_LIGHT)
        ax.plot(position, reference, color=COLOR_REFERENCE_LAP, linewidth=1.5, label="Лучший круг")
        ax.plot(position, analysed, color=COLOR_ANALYSED_LAP, linewidth=1.5, label="Этот круг")
        ax.set_ylabel(ylabel, color=TEXT_SECONDARY, fontsize=9)
        ax.grid(True, color=GRID_LINE, linewidth=0.5)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(GRID_LINE)

    def _plot_pedals(self, ax, position, analysed) -> None:
        ax.set_facecolor(SURFACE_LIGHT)
        ax.fill_between(position, 0, analysed["gas"], color=COLOR_ANALYSED_LAP, alpha=0.5, step="mid", label="Газ")
        ax.fill_between(position, 0, -analysed["brake"], color=COLOR_LOSING_TIME, alpha=0.5, step="mid", label="Тормоз")
        ax.set_ylabel("Газ / тормоз", color=TEXT_SECONDARY, fontsize=9)
        ax.set_ylim(-1.05, 1.05)
        ax.grid(True, color=GRID_LINE, linewidth=0.5)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(GRID_LINE)

    def _plot_delta(self, ax, position, delta_ms) -> None:
        ax.set_facecolor(SURFACE_LIGHT)
        ax.plot(position, delta_ms, color=COLOR_LOSING_TIME, linewidth=1.5)
        ax.axhline(0, color=GRID_LINE, linewidth=1)
        ax.set_ylabel("Дельта, мс", color=TEXT_SECONDARY, fontsize=9)
        ax.grid(True, color=GRID_LINE, linewidth=0.5)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(GRID_LINE)
