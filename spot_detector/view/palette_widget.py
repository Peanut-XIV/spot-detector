import sys
from typing import TypeGuard

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
    QMainWindow,
    QApplication,
)

from spot_detector.model.models import Shade, homogenous_color_table
from spot_detector.view.base_list_widget import MoveListWidget


class Palette_List(MoveListWidget):
    palette_changed = Signal(list)

    def __init__(
        self,
        shades: list[Shade] | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.create_actions()

        if shades is not None:
            self.set_palette(shades)

    def create_actions(self):
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

    def get_shade_list(self) -> list[Shade]:
        output = []
        items = [self.item(i) for i in range(self.count())]
        valid_items = filter(is_palette_item, items)
        sorted_items = sorted(valid_items, key=lambda x: x.index)
        output = [item.shade.model_copy(deep=True) for item in sorted_items]
        return output

    @Slot(list)
    def set_palette(self, shades: list[Shade]):
        """
        data contains the color value of each label in the BGR format
        """
        self.clear()
        for i, row in enumerate(shades):
            Palette_Item(i, row, self)
        self.show()

    @Slot()
    def incr_sel_ID(self):
        sel_items = self.selectedItems()
        for e in sel_items:
            if isinstance(e, Palette_Item):
                e.incr_label()
        if len(sel_items) > 0:
            self.palette_changed.emit(self.get_shade_list())

    @Slot()
    def decr_sel_ID(self):
        sel_items = self.selectedItems()
        for e in self.selectedItems():
            if isinstance(e, Palette_Item):
                e.decr_label()
        if len(sel_items) > 0:
            self.palette_changed.emit(self.get_shade_list())

    def selected_rows(self):
        items = self.selectedItems()
        selected = [False] * self.count()
        for item in items:
            if isinstance(item, Palette_Item):
                selected[item.index] = True
        return selected


class Palette_Item(QListWidgetItem):
    def __init__(
        self,
        index: int,
        shade: Shade,
        listview: QListWidget | None = None,
    ):
        # ColorTable is coded with 16 bits per channel the value is converted
        # to 8 bit to generate a thumbnail the 8 bit values are discarded and
        # the 16 bit values are kept

        image = QImage(50, 50, QImage.Format.Format_RGBA8888)
        r, g, b = shade.rgb_u8
        image.fill(QColor(r, g, b, 255))

        super().__init__(QPixmap(image), str(shade.label_id), listview)

        self.index: int = index
        self.shade = shade.model_copy()
        self.update_text()

    def incr_label(self):
        self.shade.label_id += 1
        self.update_text()

    def decr_label(self):
        self.shade.label_id = max(0, self.shade.label_id - 1)
        self.update_text()

    def default_label(self):
        self.shade.label_id = 0
        self.update_text()

    def update_text(self):
        self.setText(str(self.shade.label_id))


def clamp(val: int, interval: tuple[int, int]) -> int:
    mn, mx = min(interval), max(interval)
    return max(mn, min(val, mx))


def convert_channel_u16_u8(val: int) -> int:
    val = clamp(val, (0, 65535))
    val = val >> 8
    return val


def is_palette_item(item: QListWidgetItem) -> TypeGuard[Palette_Item]:
    return isinstance(item, Palette_Item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    table = [Shade.from_row(row) for row in homogenous_color_table(3)]
    palette = Palette_List(table, window)
    window.setCentralWidget(palette)
    window.show()
    sys.exit(app.exec())
