"""Track map colored by where the analysed lap is losing or gaining time
relative to the theoretical optimal lap (diverging encoding: red = losing,
blue = gaining, gray = on pace).
"""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from motorai.ui.palette import (
    COLOR_GAINING_TIME,
    COLOR_LOSING_TIME,
    COLOR_NEUTRAL,
    SURFACE_LIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class TrackMapWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._figure = Figure(figsize=(5, 5), facecolor=SURFACE_LIGHT)
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)

    def set_data(
        self,
        car_x: np.ndarray,
        car_z: np.ndarray,
        delta_rate: np.ndarray,
        apex_points: list[tuple[int, float, float]] | None = None,
    ) -> None:
        """``delta_rate`` is the per-bin rate of change of the delta trace
        (positive = losing time right here, negative = gaining it) — using
        the local rate rather than the cumulative delta so color reflects
        *this* stretch of track, not how far behind the whole lap already is.

        ``apex_points`` is ``[(corner_index, x, z), ...]`` — where each
        detected corner's apex actually is, marked directly on the map so
        it doesn't have to be inferred from the data.
        """
        self._figure.clear()
        ax = self._figure.add_subplot(111, facecolor=SURFACE_LIGHT)

        points = np.column_stack([car_x, car_z]).reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        smoothed = _smooth(delta_rate, window=9)
        limit = max(abs(np.percentile(smoothed, 2)), abs(np.percentile(smoothed, 98)), 1e-6)
        norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
        cmap = _diverging_colormap()

        lc = LineCollection(segments, cmap=cmap, norm=norm, linewidths=3)
        lc.set_array(smoothed[:-1])
        ax.add_collection(lc)

        for corner_index, x, z in apex_points or []:
            ax.scatter([x], [z], s=36, facecolor=SURFACE_LIGHT, edgecolor=TEXT_PRIMARY, linewidth=1.5, zorder=5)
            ax.annotate(
                str(corner_index),
                (x, z),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=8,
                color=TEXT_PRIMARY,
                fontweight="bold",
            )

        ax.set_xlim(car_x.min() - 20, car_x.max() + 20)
        ax.set_ylim(car_z.min() - 20, car_z.max() + 20)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(
            "Трасса: красный — теряешь время, синий — быстрее идеала. Точки — апексы поворотов",
            color=TEXT_SECONDARY,
            fontsize=9,
        )

        self._canvas.draw()


def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    kernel = np.ones(window) / window
    padded = np.pad(values, window, mode="edge")
    return np.convolve(padded, kernel, mode="same")[window:-window]


def _diverging_colormap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        "motorai_diverging", [COLOR_GAINING_TIME, COLOR_NEUTRAL, COLOR_LOSING_TIME]
    )
