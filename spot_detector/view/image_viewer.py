import sys

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRectF, QSize, Slot
from PySide6.QtGui import (
    QAction,
    QIcon,
    QImage,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QToolBar,
)
import spot_detector.rc_resources


class ImageView(QGraphicsView):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.scale_power = 0
        self.scale_factor = 1.1
        self._image_item = QGraphicsPixmapItem()
        scene = QGraphicsScene(self)
        scene.addItem(self._image_item)
        self.setScene(scene)
        self.change_transform(-2)
        self.setMinimumWidth(200)

    def change_transform(self, value: int):
        self.scale_power = max(-10, min(10, value))
        k = self.scale_factor**self.scale_power
        transform = QTransform(k, 0, 0, 0, k, 0, 0, 0, 1)
        self.setTransform(transform)
        self.updateScene([self.scene().sceneRect()])

    @Slot()
    def zoom_in(self):
        self.change_transform(self.scale_power + 1)

    @Slot()
    def zoom_out(self):
        self.change_transform(self.scale_power - 1)

    @Slot()
    def zoom_neutral(self):
        self.change_transform(0)


class ViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        v_layout = QVBoxLayout(self)
        self.viewer: ImageView = ImageView()
        self.create_toolbar()
        # Replace with toolbar
        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.viewer)
        self.setLayout(v_layout)

        self.frame0: QImage = QImage(":resources/images/testscreen.png")
        self.show_frame0()

    def create_toolbar(self):
        self.create_actions()
        self.toolbar = QToolBar("Image Viewer", self)
        self.toolbar.addActions(
            [self.zoom_out_action, self.zoom_neutral_action, self.zoom_in_action]
        )

    def create_actions(self):
        icon_i = QIcon(":resources/images/loupe_plus.png")
        self.zoom_in_action = QAction(icon_i, "Zoom In", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(self.viewer.zoom_in)

        icon_o = QIcon(":resources/images/loupe_moins.png")
        self.zoom_out_action = QAction(icon_o, "Zoom Out", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self.viewer.zoom_out)

        icon_n = QIcon(":resources/images/loupe_neutre.png")
        self.zoom_neutral_action = QAction(icon_n, "Zoom Neutral", self)
        self.zoom_neutral_action.setShortcut("Ctrl+o")
        self.zoom_neutral_action.triggered.connect(self.viewer.zoom_neutral)

    def show_frame0(self):
        size = self.frame0.size()
        self.viewer.setSceneRect(QRectF(0, 0, size.width(), size.height()))
        self.viewer._image_item.setPixmap(QPixmap(self.frame0))

    @Slot(QImage)
    def show_image(self, image: QImage):
        self.frame0 = image.copy()
        self.show_frame0()


if __name__ == "__main__":
    app = QApplication()
    mainWidget = ViewerWidget()
    mainWidget.show()
    sys.exit(app.exec())
