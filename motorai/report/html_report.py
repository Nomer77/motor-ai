"""Renders a session analysis as a single self-contained HTML file (charts
embedded as base64 PNGs) — for sharing or archiving without the desktop app.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib.figure import Figure

from motorai.analysis.summary import SessionReport
from motorai.ui.palette import (
    COLOR_ANALYSED_LAP,
    COLOR_CRITICAL,
    COLOR_GOOD,
    COLOR_LOSING_TIME,
    COLOR_REFERENCE_LAP,
    GRID_LINE,
    SURFACE_LIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def generate_html_report(report: SessionReport, out_path: Path) -> None:
    analysed_lap = report.resampled_laps[report.analysed_lap_number]
    reference_lap = report.resampled_laps[report.reference_lap_number]
    delta = report.delta_trace_ms.to_numpy()

    chart_png_b64 = _render_chart_png(analysed_lap, reference_lap, delta)

    rows = "\n".join(
        f"<tr><td>{t.corner_index}</td><td class='{_loss_class(t.time_loss_ms)}'>{t.time_loss_ms:+.0f}</td>"
        f"<td>{t.text.split(' — ', 1)[-1]}</td></tr>"
        for t in report.tips
    )

    html = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>MotorAI — {report.track}</title>
<style>
  body {{ background:{SURFACE_LIGHT}; color:{TEXT_PRIMARY}; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 2rem; }}
  h1 {{ font-size: 1.3rem; }}
  .summary {{ color:{TEXT_SECONDARY}; margin-bottom: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid {GRID_LINE}; }}
  th {{ color:{TEXT_SECONDARY}; font-weight: 600; }}
  td.loss-high {{ color:{COLOR_CRITICAL}; font-weight: 600; }}
  td.loss-gain {{ color:{COLOR_GOOD}; font-weight: 600; }}
  img {{ max-width: 100%; margin: 1rem 0; }}
</style></head>
<body>
  <h1>{report.track} — {report.car}</h1>
  <p class="summary">
    Круг {report.analysed_lap_number}: {report.analysed_lap_time_ms / 1000:.3f} с &nbsp;•&nbsp;
    Теоретический идеал: {report.theoretical_best_ms / 1000:.3f} с &nbsp;•&nbsp;
    Отставание: {report.gap_to_theoretical_ms / 1000:+.3f} с &nbsp;•&nbsp;
    эталонный круг — №{report.reference_lap_number}
  </p>
  <img src="data:image/png;base64,{chart_png_b64}" alt="Телеметрия круга">
  <table>
    <thead><tr><th>Поворот</th><th>Потеря, мс</th><th>Совет</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body></html>
"""
    out_path.write_text(html, encoding="utf-8")


def _loss_class(loss_ms: float) -> str:
    if loss_ms > 50:
        return "loss-high"
    if loss_ms < 0:
        return "loss-gain"
    return ""


def _render_chart_png(analysed_lap, reference_lap, delta: np.ndarray) -> str:
    figure = Figure(figsize=(9, 7), facecolor=SURFACE_LIGHT)
    axes = figure.subplots(3, 1, sharex=True)
    position = analysed_lap["position"].to_numpy()

    axes[0].set_facecolor(SURFACE_LIGHT)
    axes[0].plot(position, reference_lap["speed_kmh"], color=COLOR_REFERENCE_LAP, linewidth=1.5, label="Лучший круг")
    axes[0].plot(position, analysed_lap["speed_kmh"], color=COLOR_ANALYSED_LAP, linewidth=1.5, label="Этот круг")
    axes[0].set_ylabel("Скорость, км/ч", color=TEXT_SECONDARY)
    axes[0].legend(loc="lower right", fontsize=8, frameon=False)

    axes[1].set_facecolor(SURFACE_LIGHT)
    axes[1].fill_between(position, 0, analysed_lap["gas"], color=COLOR_ANALYSED_LAP, alpha=0.5, step="mid", label="Газ")
    axes[1].fill_between(position, 0, -analysed_lap["brake"], color=COLOR_LOSING_TIME, alpha=0.5, step="mid", label="Тормоз")
    axes[1].set_ylabel("Газ / тормоз", color=TEXT_SECONDARY)

    axes[2].set_facecolor(SURFACE_LIGHT)
    axes[2].plot(position, delta, color=COLOR_LOSING_TIME, linewidth=1.5)
    axes[2].axhline(0, color=GRID_LINE, linewidth=1)
    axes[2].set_ylabel("Дельта, мс", color=TEXT_SECONDARY)
    axes[2].set_xlabel("Позиция на круге", color=TEXT_SECONDARY)

    for ax in axes:
        ax.grid(True, color=GRID_LINE, linewidth=0.5)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(GRID_LINE)

    figure.tight_layout()

    buf = io.BytesIO()
    figure.savefig(buf, format="png", dpi=130)
    return base64.b64encode(buf.getvalue()).decode("ascii")
