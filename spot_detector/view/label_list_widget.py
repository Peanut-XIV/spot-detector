import sys
from typing import TypeGuard

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtCore import Signal, Slot, Qt, QItemSelectionModel
from PySide6.QtGui import QIcon, QPixmap

from spot_detector.model.models import DetParams
from spot_detector import rc_icons


class LabelListItem(QListWidgetItem):
    def __init__(
        self,
        index: int,
        model: DetParams,
        focused: bool = False,
        listview: QListWidget | None = None,
    ):
        self.checked_icon = QIcon(":resources/icons/select_on_64.png")
        self.unchecked_icon = QPixmap(":resources/icons/select_off_64.png")
        icon = self.checked_icon if focused else self.unchecked_icon
        name_str = f"{index + 1} - {model.color_name}"
        super().__init__(icon, name_str, listview)

        self.index: int = index
        self.model = model.model_copy(deep=True)
        self.update_text()

    @Slot()
    def update_text(self):
        name_str = f"{self.index} - {self.model.color_name}"
        self.setText(name_str)

    @Slot(bool)
    def set_focused_state(self, focused: bool):
        if focused:
            self.setIcon(self.checked_icon)
        else:
            self.setIcon(self.unchecked_icon)

    def set_index(self, index: int):
        self.index = index
        self.update_text()


class LabelListWidget(QListWidget):
    update_names: Signal = Signal()

    def __init__(
        self,
        model: list[DetParams],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.focused_item: LabelListItem
        self.set_list(model)
        self.itemDoubleClicked.connect(self.onItemDoubleClicked)

    def set_list(self, entries: list[DetParams]):
        self.clear()
        for i, model in enumerate(entries):
            if i == 0:
                item = LabelListItem(i, model, True, self)
                self.focused_item = item
            else:
                item = LabelListItem(i, model, False, self)
            self.update_names.connect(item.update_text)
        self.show()

    @property
    def focused_item_index(self) -> int:
        return self.indexFromItem(self.focused_item).row()

    def get_list(self) -> list[DetParams]:
        output = []
        items = [self.item(i) for i in range(self.count())]
        valid_items = filter(is_label_list_item, items)
        output = [item.model.model_copy(deep=True) for item in valid_items]
        return output

    def _get_items(self) -> list[LabelListItem]:
        items = [self.item(row) for row in range(self.count())]
        items = filter(is_label_list_item, items)
        return list(items)

    def set_focused_item(self, item: QListWidgetItem):
        prev_focused = self.focused_item
        if prev_focused is item:
            return
        if not is_label_list_item(item):
            return
        if prev_focused is not None:
            prev_focused.set_focused_state(False)
        item.set_focused_state(True)
        self.focused_item = item

    @Slot()
    def reindex_items(self):
        for item in self._get_items():
            idx = self.indexFromItem(item).row()
            item.set_index(idx)

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

        self.reindex_items()

        # reconstitute selection
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

        self.reindex_items()

        # reconstitute selection
        selection_model = self.selectionModel()
        selection_model.clear()
        for e in items:
            idx = self.indexFromItem(e)
            selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select)

    @Slot(QListWidgetItem)
    def onItemDoubleClicked(self, item: QListWidgetItem):
        if not is_label_list_item(item):
            return
        self.set_focused_item(item)

    @Slot()
    def insert_new_after_focused_item(self):
        next_idx = self.focused_item_index + 1
        model = DetParams.from_prepopulated_defaults(next_idx + 1)
        item = LabelListItem(next_idx, model, False, None)
        self.insertItem(next_idx, item)
        self.reindex_items()

    @Slot()
    def add_new_item(self):
        idx = self.count()
        model = DetParams.from_prepopulated_defaults(idx + 1)
        LabelListItem(idx, model, False, self)
        self.reindex_items()

    @Slot()
    def duplicate_focused_item(self):
        item = self.focused_item
        model = item.model.model_copy(deep=True)
        model.color_name = model.color_name + "(copy)"
        next_idx = self.focused_item_index + 1
        item = LabelListItem(next_idx, model, False, self)
        self.reindex_items()

    @Slot()
    def delete_focused_item(self):
        # TODO: Bugged af
        items = self._get_items()
        if len(items) <= 1:
            return
        idx = self.focused_item_index
        self.takeItem(idx)
        if idx == self.count():
            idx -= 1

        self.reindex_items()

        new_focus = self.item(idx)
        if is_label_list_item(new_focus):
            new_focus.set_focused_state(True)
            return

        items = self._get_items()
        new_focus = items[0]
        new_focus.set_focused_state(True)
        self.focused_item = new_focus

    @Slot()
    def update_focused_item_name(self):
        self.focused_item.update_text()


def is_label_list_item(item: QListWidgetItem) -> TypeGuard[LabelListItem]:
    return isinstance(item, LabelListItem)


class LabelWidget(QWidget):
    def __init__(
        self,
        model: list[DetParams],
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        l1 = QVBoxLayout(self)

        self.list = LabelListWidget(model, parent)
        l1.addWidget(self.list)

        l2 = QHBoxLayout(self)
        # TODO: create actions beforehand with attributed names, hover, icons...
        self.remove_button = QPushButton("Remove", self)
        self.add_button = QPushButton("Add", self)
        l2.addWidget(self.remove_button)
        l2.addWidget(self.add_button)
        l2.addStretch()

        self.duplicate_button = QPushButton("Duplicate", self)
        self.insert_button = QPushButton("Insert", self)
        l2.addWidget(self.duplicate_button)
        l2.addWidget(self.insert_button)
        l1.addLayout(l2)

        self.remove_button.clicked.connect(self.list.delete_focused_item)

        self.setLayout(l1)


if __name__ == "__main__":
    model = []
    for i in range(10):
        model.append(DetParams.from_prepopulated_defaults(i + 1))

    app = QApplication(sys.argv)
    win = LabelWidget(model)
    win.show()
    sys.exit(app.exec())
