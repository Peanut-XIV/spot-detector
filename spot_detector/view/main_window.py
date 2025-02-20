from pathlib import Path
import sys
import random

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
    QPixmap,
    QColor,
    QIcon,
    QImage,
)

from spot_detector.model.project import Project
from spot_detector.view.dialogs import ReadOnlyImageFileDialog
from spot_detector.view.image_viewer import ViewerWidget
from spot_detector.view.kmeans_dialog import KMeansDialog, KmeansProcessor
from spot_detector import rc_resources
from spot_detector.view.palette_widget import Palette_List, Palette_Item


class MainWindow(QMainWindow):
    def __init__(self, project: Project):
        super().__init__()
        self.setWindowTitle("Spot Detector GUI")
        self.project = project

        splitter = QSplitter(Qt.Orientation.Horizontal)
        print("creating viewer")
        self._create_viewer(splitter)
        print("creating palette")
        self._create_palette(splitter)
        print("creating menus")
        self._create_menu()
        print("composing")
        splitter.addWidget(self.palette_list)
        splitter.addWidget(self.viewer)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        self.setCentralWidget(splitter)

    def _create_palette(self, parent):
        self.palette_list = Palette_List(parent)
        for _ in range(10):
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            item = Palette_Item(r, g, b, 0, self.palette_list)

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
        self.palette_menu = self.menu.addMenu("Palette")
        self.palette_menu.addActions(
            [
                self.palette_list.move_sel_up_action,
                self.palette_list.move_sel_down_action,
                self.palette_list.incr_sel_action,
                self.palette_list.decr_sel_action,
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
        # As BGR and max depth up to uint16 channel depth
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
        self.project.set_ref_image_path(file)
        # Show image in viewer
        self.set_ref_image_array(image)
        self.viewer.show_image(self.ref_image_paintable)

    def set_ref_image_array(self, array: NDArray):
        self.ref_image_array: NDArray = array
        self.ref_image_paintable: QImage
        if array.dtype != np.uint8:
            if array.dtype == np.uint16:
                array = np.right_shift(array, 8).astype(np.uint8)
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
            thread = KmeansProcessor(self.ref_image_array, dialog.get_value(), self)
            thread.result_ready.connect(self.handle_kmeans_output)
            thread.finished.connect(thread.deleteLater)
            thread.run()

    @Slot(object)
    def handle_kmeans_output(self, output: tuple[NDArray, NDArray, NDArray]):
        # set color table
        self.project.set_lut(output[0])
        self.palettized_ref_array = output[1]
        self.labeled_ref_array = output[2]
        if output[0].dtype == np.uint16:
            processed_output = (output[0] >> 8).astype(np.uint8)
        else:
            processed_output = output[0]
        listified = [list(row) + [0] for row in processed_output]
        self.palette_list.set_palette(listified)
        # TODO: handle it really


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(Project.from_path("test_file"))
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
