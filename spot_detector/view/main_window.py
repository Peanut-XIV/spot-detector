import json
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
    QDialog,
    QMainWindow,
    QSplitter,
    QMessageBox,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
    QImage,
)

from spot_detector.model.defaults import PROJECTS_LIST, get_recent_project_paths
from spot_detector.model.project import Project
from spot_detector.transformations import label_img_fastest
from spot_detector.view.dialogs import (
    ConfirmOverwriteDialog,
    ReadOnlyImageFileDialog,
    SaveProjectAsDialog,
)
from spot_detector.view.image_viewer import ViewerWidget
from spot_detector.view.kmeans_dialog import KMeansDialog, KmeansProcessor
from spot_detector import rc_resources  # WARN: Do not remove
from spot_detector.view.palette_widget import Palette_List, Palette_Item


class MainWindow(QMainWindow):
    def __init__(self, project: Project):
        super().__init__()
        self.setWindowTitle("Spot Detector GUI")
        self.project = project

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._create_viewer(splitter)
        self._create_palette(splitter)
        self._create_menu()
        splitter.addWidget(self.palette_list)
        splitter.addWidget(self.viewer)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        self.setCentralWidget(splitter)

        self.previous_rows = None  # The rows previously selected for highlight

    def _create_palette(self, parent):
        self.palette_list = Palette_List(parent)
        for i in range(10):
            color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )
            item = Palette_Item(i, color, 0, self.palette_list)

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
        self.viewer.request_palettized.connect(self.make_palettized_ref)
        self.viewer.request_highlight.connect(self.make_highlight)

    @Slot()
    def make_highlight(self):
        rows = self.palette_list.selected_rows()
        if rows == self.previous_rows:
            self.viewer.show_highlight()
        mod_palette = []
        if self.project.configuration is None:
            # TODO: Display error message (no palette yet -> needs ref image)
            return
        for sel, row in zip(rows, self.project.configuration.color_data.table):
            if sel:
                mod_palette.append([0, 0, 255])
            else:
                mod_palette.append(row[0:3])
        mod_lut = np.array(mod_palette, dtype=np.uint8)
        labeled_array = self.get_labeled_ref_array()
        if labeled_array is None:
            # No ref array
            return
        print("reference:", labeled_array.shape, labeled_array.dtype)
        print("mod_lut:", mod_lut.shape, mod_lut.dtype)
        out = mod_lut[labeled_array]
        self.viewer.set_highlight(
            QImage(
                out.data,
                out.shape[1],
                out.shape[0],
                QImage.Format.Format_BGR888,
            )
        )
        self.viewer.show_highlight()

    @Slot()
    def make_palettized_ref(self):
        # get lut
        if self.project.configuration is None:
            return  # TODO: display a message
        lut = np.array(
            self.project.configuration.color_data.table,
            dtype=np.uint8,
        )[:, 0:3]
        ref = self.ref_image_array
        if ref.dtype == np.uint16:
            ref = (ref >> 8).astype(np.uint8)
        elif ref.dtype != np.uint8:
            return  # TODO: display a message too
        print("reference:", ref.shape, ref.dtype)
        print("palette:", lut.shape, lut.dtype)
        labels = label_img_fastest(ref, lut)
        palettized = lut[labels]
        print(palettized.shape)
        drawable = QImage(
            palettized.data,
            palettized.shape[1],
            palettized.shape[0],
            QImage.Format.Format_BGR888,
        )
        self.viewer.set_palettized_ref(drawable)
        self.viewer.show_palettized()

    @Slot()
    def dialog_save_project_as(self):
        dialog = SaveProjectAsDialog()
        if not dialog.exec():
            return
        pathes = dialog.selectedFiles()
        if len(pathes) != 1:
            msg = QMessageBox(self)
            msg.setText("Unexpected amount of files selected")
            msg.exec()
            return
        path = Path(pathes[0])
        if path.exists():
            conf_diag = ConfirmOverwriteDialog(path, self)
            if conf_diag.exec() == QDialog.DialogCode.Rejected:
                return
        self.project.latest_save_path = str(path)
        with open(path, "w", encoding="UTF-8") as file:
            json.dump(self.project.model_dump(), file)
        # add path to existing projects
        if str(path) not in get_recent_project_paths():
            with open(PROJECTS_LIST, "a", encoding="UTF-8") as file:
                file.write(str(path) + "\n")

    @Slot()
    def get_labeled_ref_array(self):
        if self.labeled_ref_array is None:
            img = self.ref_image_array.astype(np.uint8)
            if self.project.configuration is not None:
                color_table = np.array(
                    self.project.configuration.color_data.table
                ).astype(np.uint8)
            else:
                return None
            self.labeled_ref_array = label_img_fastest(img, color_table).astype(
                np.uint8
            )
        return self.labeled_ref_array.astype(np.uint8)

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
        self.viewer.set_ref_image(self.ref_image_paintable)

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
        self.palettized_ref_array = output[1]
        self.labeled_ref_array = (
            output[2].reshape(self.palettized_ref_array.shape[0:2]).astype(np.uint8)
        )
        if output[0].dtype == np.uint16:
            processed_output = (output[0] >> 8).astype(np.uint8)
        else:
            processed_output = output[0]
        listified = [list(row) + [0] for row in processed_output]
        self.project.set_lut(listified)
        self.palette_list.set_palette(listified)
        # TODO: handle it really


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(Project.from_path("test_file"))
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
