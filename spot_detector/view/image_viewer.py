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
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QToolBar,
)
from spot_detector.model.project import Project
from spot_detector import rc_resources, rc_icons  # WARN: do not remove


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

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)

        v_layout = QVBoxLayout(self)
        self.viewer: ImageView = ImageView()
        self.project = project
        self.create_toolbar()
        # Replace with toolbar
        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.viewer)
        self.setLayout(v_layout)

        self.reference_image: QPixmap = QPixmap(
            QImage(":resources/images/testscreen.png")
        )
        self.palettized_reference: QPixmap | None = None
        self.highlight: QPixmap | None = None

        self.current_image = self.reference_image

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
        self.show_ref_action.triggered.connect(self.show_reference_image)

        self.show_palettized_action = QAction("Show Palettized", self)
        self.show_palettized_action.triggered.connect(self.request_palettized.emit)

        self.show_highlight_action = QAction("Show Highlight", self)
        self.show_highlight_action.triggered.connect(self.request_highlight.emit)

    @Slot()
    def show_init(self):
        size = self.reference_image.size()
        self.viewer.setSceneRect(QRectF(0, 0, size.width(), size.height()))
        self.viewer._image_item.setPixmap(self.reference_image)

    @Slot(bool)
    def update_reference(self, msg_on_fail: bool = True):
        if self.project.reference_image_model is None:
            if msg_on_fail:
                need_ref_image_msg(self)
            return

        self.reference_image = QPixmap(
            self.project.reference_image_model.mats.reference.image
        )
        size = self.reference_image.size()
        self.viewer.setSceneRect(QRectF(0, 0, size.width(), size.height()))
        self.show_reference_image()

    @Slot(bool)
    def update_palettized(self, msg_on_fail: bool = True):
        if self.project.reference_image_model is None:
            if msg_on_fail:
                need_ref_image_msg(self)
            return
        if self.project.reference_image_model.mats.palettized is None:
            if msg_on_fail:
                box = QMessageBox(self)
                box.setWindowTitle("Error: missing palette")
                box.setText(
                    "This action is impossible. Please generate a palette"
                    " first by computing the k-means of the reference image."
                )
                box.exec()
            return

        self.palettized_reference = QPixmap(
            self.project.reference_image_model.mats.palettized.image
        )

    @Slot(bool)
    def update_highlight(self, msg_on_fail: bool = True):
        if self.project.reference_image_model is None:
            if msg_on_fail:
                need_ref_image_msg(self)
            return
        if self.project.reference_image_model.mats.highlight is None:
            if msg_on_fail:
                print(
                    "unexpectedly, reference_image_model.mats.highlight is still None"
                )
                need_labels_msg(self)
            return
        self.highlight = QPixmap(
            self.project.reference_image_model.mats.highlight.image
        )

    def show_reference_image(self):
        self.viewer._image_item.setPixmap(self.reference_image)

    def show_highlight(self):
        if self.highlight is not None:
            self.viewer._image_item.setPixmap(self.highlight)

    def show_palettized_reference(self):
        if self.palettized_reference is not None:
            self.viewer._image_item.setPixmap(self.palettized_reference)

    def reset_highlight(self):
        self.highlight = None
        self.viewer._image_item.setPixmap(self.reference_image)

    def reset_palettized(self):
        self.palettized_reference = None
        self.reset_highlight()


def need_ref_image_msg(parent: QWidget):
    box = QMessageBox(parent)
    box.setWindowTitle("Error: Missing reference image")
    box.setText(
        "This action is impossible, please select a reference image and try again."
    )
    box.exec()


def need_labels_msg(parent: QWidget):
    box = QMessageBox(parent)
    box.setWindowTitle("Error: missing labels")
    box.setText(
        "This action is impossible because it needs the reference image to be "
        "labeled. Please generate labels by applying the current palette or by "
        "creating a new one. A palette can be created from computing the k-means "
        "of the reference image."
    )
    box.exec()


if __name__ == "__main__":
    app = QApplication()
    project = Project(name="standalone test")
    mainWidget = ViewerWidget(project)
    mainWidget.show()
    sys.exit(app.exec())
