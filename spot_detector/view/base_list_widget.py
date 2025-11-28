from abc import abstractmethod
import sys

from PySide6.QtCore import QItemSelectionModel, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QListWidget,
    QWidget,
)


class MoveListWidget(QListWidget):
    def __init__(
        self,
        parent: QWidget | None,
    ) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.create_move_actions()

    def create_move_actions(self):
        self.move_sel_up_action = QAction("Move Selection Up", self)
        self.move_sel_up_action.triggered.connect(self.move_sel_up)
        self.move_sel_down_action = QAction("Move Selection Down", self)
        self.move_sel_down_action.triggered.connect(self.move_sel_down)

    @Slot()
    def move_sel_up(self):
        items = self.selectedItems()
        idx_item = [(self.indexFromItem(item).row(), item) for item in items]
        idx_item.sort(key=lambda x: x[0])
        for _, item in idx_item:
            idx = self.indexFromItem(item)
            prev_row = idx.row() - 1
            prev_idx = idx.siblingAtRow(prev_row)
            if not prev_idx.isValid():
                continue
            if self.itemFromIndex(prev_idx) in items:
                continue
            self.takeItem(idx.row())
            self.insertItem(prev_row, item)
        selection_model = self.selectionModel()
        selection_model.clear()
        for e in items:
            idx = self.indexFromItem(e)
            selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select)

    @Slot()
    def move_sel_down(self):
        items = self.selectedItems()
        idx_item = [(self.indexFromItem(item).row(), item) for item in items]
        idx_item.sort(key=lambda x: x[0])
        idx_item.reverse()
        for _, item in idx_item:
            idx = self.indexFromItem(item)
            next_row = idx.row() + 1
            next_idx = idx.siblingAtRow(next_row)
            if not next_idx.isValid():
                continue
            if self.itemFromIndex(next_idx) in items:
                continue
            self.takeItem(idx.row())
            self.insertItem(next_row, item)
        selection_model = self.selectionModel()
        selection_model.clear()
        for e in items:
            idx = self.indexFromItem(e)
            selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select)
