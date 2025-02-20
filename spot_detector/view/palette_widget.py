import sys
import random
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
    QMainWindow,
    QApplication,
)

from PySide6.QtCore import (
    QItemSelectionModel,
    Qt,
    Signal,
    Slot,
)

from PySide6.QtGui import (
    QAction,
    QColor,
    QImage,
    QKeyEvent,
    QPixmap,
)


class Palette_List(QListWidget):
    palette_changed = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.create_actions()

    def create_actions(self):
        self.move_sel_up_action = QAction("Move Selection Up", self)
        self.move_sel_up_action.triggered.connect(self.move_sel_up)
        self.move_sel_down_action = QAction("Move Selection Down", self)
        self.move_sel_down_action.triggered.connect(self.move_sel_down)
        self.incr_sel_action = QAction("Increment Selection Label", self)
        self.incr_sel_action.triggered.connect(self.incr_sel_ID)
        self.decr_sel_action = QAction("Decrement Selection Label", self)
        self.decr_sel_action.triggered.connect(self.decr_sel_ID)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Up:
            self.move_sel_up_action.trigger()
        elif key == Qt.Key.Key_Down:
            # call action move down
            self.move_sel_down_action.trigger()
        elif key == Qt.Key.Key_Right:
            # call action increase ID
            self.incr_sel_action.trigger()
        elif key == Qt.Key.Key_Left:
            # call action decrease ID
            self.decr_sel_action.trigger()

    def get_palette(self) -> list[list[int]]:
        output = []
        for i in range(self.count()):
            item = self.item(i)
            if isinstance(item, Palette_Item):
                output.append(item.color + [item.label])
        return output

    @Slot(list)
    def set_palette(self, data: list[list[int]]):
        self.clear()
        for row in data:
            if len(row) != 4:
                print("dropped row:", row)
                continue
            Palette_Item(row[2], row[1], row[0], row[3], self)
        self.show()

    @Slot()
    def move_sel_up(self):
        items = self.selectedItems()
        idx_item = [(self.indexFromItem(item).row(), item) for item in items]
        idx_item.sort(key=lambda x: x[0])
        changed = False
        for _, item in idx_item:
            idx = self.indexFromItem(item)
            prev_row = idx.row() - 1
            prev_idx = idx.siblingAtRow(prev_row)
            if not prev_idx.isValid():
                continue
            if self.itemFromIndex(prev_idx) in items:
                continue
            changed = True
            self.takeItem(idx.row())
            self.insertItem(prev_row, item)
        selection_model = self.selectionModel()
        selection_model.clear()
        for e in items:
            idx = self.indexFromItem(e)
            selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select)
        if changed:
            self.palette_changed.emit(self.get_palette())

    @Slot()
    def move_sel_down(self):
        items = self.selectedItems()
        idx_item = [(self.indexFromItem(item).row(), item) for item in items]
        idx_item.sort(key=lambda x: x[0])
        idx_item.reverse()
        changed = False
        for _, item in idx_item:
            idx = self.indexFromItem(item)
            next_row = idx.row() + 1
            next_idx = idx.siblingAtRow(next_row)
            if not next_idx.isValid():
                continue
            if self.itemFromIndex(next_idx) in items:
                continue
            changed = True
            self.takeItem(idx.row())
            self.insertItem(next_row, item)
        selection_model = self.selectionModel()
        selection_model.clear()
        for e in items:
            idx = self.indexFromItem(e)
            selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select)
        if changed:
            self.palette_changed.emit(self.get_palette())

    @Slot()
    def incr_sel_ID(self):
        sel_items = self.selectedItems()
        for e in sel_items:
            if isinstance(e, Palette_Item):
                e.incr_label()
        if len(sel_items) > 0:
            self.palette_changed.emit(self.get_palette())

    @Slot()
    def decr_sel_ID(self):
        sel_items = self.selectedItems()
        for e in self.selectedItems():
            if isinstance(e, Palette_Item):
                e.decr_label()
        if len(sel_items) > 0:
            self.palette_changed.emit(self.get_palette())


class Palette_Item(QListWidgetItem):
    def __init__(
        self,
        r: int,
        g: int,
        b: int,
        label: int = 0,
        listview: QListWidget | None = None,
    ):
        image = QImage(50, 50, QImage.Format.Format_RGBA8888)
        image.fill(QColor(r, g, b, 255))
        super().__init__(QPixmap(image), str(label), listview)
        self.label = 0
        self.color = [r, g, b]
        self.update_text()

    def incr_label(self):
        self.label += 1
        self.update_text()

    def decr_label(self):
        self.label = max(0, self.label - 1)
        self.update_text()

    def default_label(self):
        self.label = 0
        self.update_text()

    def update_text(self):
        self.setText(str(self.label))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    palette = Palette_List(window)
    window.setCentralWidget(palette)
    for _ in range(10):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        item = Palette_Item(r, g, b, 0, palette)

    window.show()
    sys.exit(app.exec())
