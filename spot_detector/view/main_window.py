from pathlib import Path
import sys

import cv2
import numpy as np
from numpy.typing import NDArray

from PySide6.QtCore import (
    Qt,
    Slot,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QMessageBox,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QImage,
)

from spot_detector.model.project import Project
from spot_detector.view.dialogs import ReadOnlyImageFileDialog
from spot_detector.view.image_viewer import ViewerWidget
from spot_detector.view.kmeans_dialog import KMeansDialog, KmeansProcessor
from spot_detector import rc_resources


class MainWindow(QMainWindow):
    def __init__(self, project: Project):
        super().__init__()
        self.setWindowTitle("Spot Detector GUI")
        self.project = project

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._create_viewer(splitter)
        self._create_menu()
        splitter.addWidget(self.viewer)
        splitter.setCollapsible(0, False)

        self.setCentralWidget(splitter)

    def _create_menu(self):
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self._create_set_ref_image_action()
        self.file_menu.addAction(self.set_ref_image_action)
        self._create_kmeans_action()
        self.file_menu.addAction(self.kmeans_action)
        self.file_menu.addAction("Quit", self.close, "Ctrl+Q")
        self.view_menu = self.menu.addMenu("View")
        self.view_menu.addActions(
            [
                self.viewer.zoom_in_action,
                self.viewer.zoom_out_action,
                self.viewer.zoom_neutral_action,
            ]
        )

    def _create_set_ref_image_action(self):
        icon = QIcon(":resources/images/ref_image_icon.png")
        action = QAction(icon, "Set Reference Image", self)
        action.triggered.connect(self.dialog_for_ref_image)
        self.set_ref_image_action = action

    def _create_kmeans_action(self):
        # icon = QIcon(":resources/images/...")
        action = QAction("Compute k-means", self)
        action.triggered.connect(self.start_kmeans_dialog)
        self.kmeans_action = action

    def _create_viewer(self, parent):
        self.viewer = ViewerWidget(parent)

    @Slot()
    def dialog_for_ref_image(self):
        dialog = ReadOnlyImageFileDialog(self, "Select a dust filter", str(Path.home()))
        if not dialog.exec():
            # no file selected
            return
        files = dialog.selectedFiles()
        if len(files) == 0:
            # impossible put who knows
            return
        file = files[0]
        # Check for file validity
        # As BGR and max depth up to uint32 channel depth
        # change channel depth depending on project settings ?
        # (settings like img depth not yet implemented)
        image = cv2.imread(file, cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH)
        if image is None:
            message = QMessageBox(self)
            message.setWindowTitle("Invalid Image")
            message.setText(
                "The selected image could not be opened.\n"
                "Maybe you lack the necessary codecs to read it, "
                "the file extension is incorrect, or the file is "
                "corrupted.\nPlease try again with a different file."
            )
            message.exec()
            return
        # at this point the image is valid
        self.project.set_ref_image(file)
        # Show image in viewer
        self.set_ref_image(image)
        self.viewer.show_image(self.ref_image_paintable)

    def set_ref_image(self, array: NDArray):
        self.ref_image_data: NDArray = array
        self.ref_image_paintable: QImage
        if array.dtype != np.uint8:
            if array.dtype == np.uint16:  # TODO: Test erreurs de data
                array = np.right_shift(array, 8, dtype=np.uint8)
            elif array.dtype == np.float32:
                array = (array * 255).astype(np.uint8)
        if len(array.shape) == 2:
            array = cv2.cvtColor(array, cv2.COLOR_GRAY2BGR)
        self.ref_image_paintable = QImage(
            array.data,
            array.shape[1],
            array.shape[0],
            QImage.Format.Format_BGR888,
        )
        self.viewer.show_image(self.ref_image_paintable)

    def start_kmeans_dialog(self):
        dialog = KMeansDialog(self)
        if dialog.exec():
            thread = KmeansProcessor(self.ref_image_data, dialog.get_value(), self)
            thread.result_ready.connect(self.handle_kmeans_output)
            thread.finished.connect(thread.deleteLater)
            thread.run()

    @Slot(object)
    def handle_kmeans_output(self, output: tuple[NDArray, NDArray, NDArray]):
        cv2.imshow("output", output[1])
        print("NOT FINAL")
        # TODO: handle it really


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(Project.from_path("test_file"))
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
