import sys

from PySide6.QtCore import QRectF, Slot, Signal
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
    QVBoxLayout,
    QWidget,
    QToolBar,
)
import spot_detector.rc_resources  # WARN: don not remove


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
        transform = QTransform(k, 0, 0, 0, k, 0, 0, 0, 1)  # 3x3 matrix
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
    request_palettized: Signal = Signal()
    request_highlight: Signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        v_layout = QVBoxLayout(self)
        self.viewer: ImageView = ImageView()
        self.create_toolbar()
        # Replace with toolbar
        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.viewer)
        self.setLayout(v_layout)

        self.original_ref: QPixmap = QPixmap(QImage(":resources/images/testscreen.png"))
        self.palettized_ref: QPixmap | None = None
        self.highlight: QPixmap | None = None

        self.current_image = self.original_ref

        self.show_init()

    def create_toolbar(self):
        self.create_actions()
        self.toolbar = QToolBar("Image Viewer", self)
        self.toolbar.addActions(
            [
                self.show_ref_action,
                self.show_palettized_action,
                self.show_highlight_action,
                self.zoom_out_action,
                self.zoom_neutral_action,
                self.zoom_in_action,
            ]
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

        icon_ref = QIcon(":resources/images/ref_image_icon.png")
        self.show_ref_action = QAction(icon_ref, "Show Ref", self)
        self.show_ref_action.triggered.connect(self.show_ref)

        self.show_palettized_action = QAction("Show Palettized", self)
        self.show_palettized_action.triggered.connect(self.request_palettized.emit)

        self.show_highlight_action = QAction("Show Highlight", self)
        self.show_highlight_action.triggered.connect(self.request_highlight.emit)

    @Slot()
    def show_init(self):
        size = self.original_ref.size()
        self.viewer.setSceneRect(QRectF(0, 0, size.width(), size.height()))
        self.viewer._image_item.setPixmap(self.original_ref)

    @Slot(QImage)
    def set_ref_image(self, image: QImage):
        self.original_ref = QPixmap(image)
        size = self.original_ref.size()
        self.viewer.setSceneRect(QRectF(0, 0, size.width(), size.height()))
        self.viewer._image_item.setPixmap(self.original_ref)

    @Slot(QImage)
    def set_palettized_ref(self, image: QImage):
        self.palettized_ref = QPixmap(image)

    @Slot(QImage)
    def set_highlight(self, image: QImage):
        self.highlight = QPixmap(image)

    def show_ref(self):
        self.viewer._image_item.setPixmap(self.original_ref)

    def show_highlight(self):
        if self.highlight is not None:
            self.viewer._image_item.setPixmap(self.highlight)

    def show_palettized(self):
        if self.palettized_ref is not None:
            self.viewer._image_item.setPixmap(self.palettized_ref)


if __name__ == "__main__":
    app = QApplication()
    mainWidget = ViewerWidget()
    mainWidget.show()
    sys.exit(app.exec())
