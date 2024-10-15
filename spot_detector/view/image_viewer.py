import sys

from PySide6.QtCore import  QRectF, QSize, Slot
from PySide6.QtGui import (
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
)


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
        k = self.scale_factor ** self.scale_power
        transform = QTransform(k, 0, 0,
                               0, k, 0,
                               0, 0, 1)
        self.setTransform(transform)
        self.updateScene([self.scene().sceneRect()])

    @Slot()
    def zoom_in(self):
        self.change_transform(self.scale_power + 1)

    @Slot()
    def zoom_out(self):
        self.change_transform(self.scale_power - 1)


class ViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        v_layout = QVBoxLayout(self)

        h_layout = QHBoxLayout(self)
        h_layout.addWidget(QLabel("Image Viewer: ", self))
        h_layout.addStretch(1)
        h_layout.addWidget(QLabel("Zoom: ", self))
        self.create_zoom_buttons()
        h_layout.addWidget(self.zoom_in_button)
        h_layout.addWidget(self.zoom_out_button)

        v_layout.addLayout(h_layout)
        self.viewer = ImageView()
        v_layout.addWidget(self.viewer)

        self.zoom_in_button.clicked.connect(self.viewer.zoom_in)
        self.zoom_out_button.clicked.connect(self.viewer.zoom_out)

    def create_zoom_buttons(self):
        self.zoom_in_button = QPushButton("+", self)
        self.zoom_in_button.setFixedSize(QSize(30, 30))
        self.zoom_out_button = QPushButton("-", self)
        self.zoom_out_button.setFixedSize(QSize(30, 30))

    def change_pixmap(self, pixmap: QPixmap):
        size = pixmap.size()
        self.viewer.setSceneRect(QRectF(0, 0, size.width(), size.height()))
        self.viewer._image_item.setPixmap(pixmap)

if __name__ == "__main__":
    app = QApplication()
    mainWidget = ViewerWidget()
    mainWidget.show()
    sys.exit(app.exec())
