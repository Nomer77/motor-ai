"""Corner-by-corner tip list, sorted worst-first (already sorted that way
by build_corner_tips) — the main actionable output of the app.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QWidget

from motorai.analysis.tips import CornerTip
from motorai.ui.palette import COLOR_CRITICAL, COLOR_GOOD

COLUMNS = ["Поворот", "Потеря, мс", "Совет"]


class CornerTableWidget(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setWordWrap(True)

    def set_tips(self, tips: list[CornerTip]) -> None:
        self.setRowCount(len(tips))
        for row, tip in enumerate(tips):
            self.setItem(row, 0, QTableWidgetItem(str(tip.corner_index)))

            loss_item = QTableWidgetItem(f"{tip.time_loss_ms:+.0f}")
            loss_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if tip.time_loss_ms > 50:
                loss_item.setForeground(_qcolor(COLOR_CRITICAL))
            elif tip.time_loss_ms < 0:
                loss_item.setForeground(_qcolor(COLOR_GOOD))
            self.setItem(row, 1, loss_item)

            text_item = QTableWidgetItem(tip.text)
            text_item.setToolTip(tip.text)
            self.setItem(row, 2, text_item)
        self.resizeRowsToContents()


def _qcolor(hex_value: str):
    from PySide6.QtGui import QColor

    return QColor(hex_value)
