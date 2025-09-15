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

from spot_detector.errors import (
    FailedOpeningError,
    ImageError,
    InvalidFormatError,
    InvalidNameError,
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

        # an array of pixel values in 8 or 16 bits, representing the original image
        self.reference_image_array: NDArray | None = None
        # a Qimage of the same array
        self.reference_image_paintable: QImage | None = None

        # an array of labels, which are numerical values that code for palette colors
        # for example: 0 -> [0, 0, 0], 1 -> [0, 0, 255], 2 -> [...], ...
        self.labeled_reference_array: NDArray | None = None

        # an array of pixel values, where the pixels were translated to the closest palette color
        self.palettized_reference_array: NDArray | None = None
        # a Qimage of the same array
        self.palettized_reference_paintable: QImage | None = None

        # A list of palette colors selected by the user
        self.previous_rows = None  # The rows previously selected for highlight

    def _create_palette(self, parent):
        """A function for populating a palette widget with random palette colors."""
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
        action.triggered.connect(self.select_reference_image)
        self.set_ref_image_action = action

    def _create_kmeans_action(self):
        # TODO: ADD ICON
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
        # WARN: A function called by user action
        #   It should handle exceptions as message boxes
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
        labeled_array = self.get_labeled_reference_array()
        if labeled_array is None:
            # No ref array
            return
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
        ref = self.reference_image_array
        if ref is None:
            return
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
        self.viewer.set_palettized_reference(drawable)
        self.viewer.show_palettized_reference()

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
    def get_labeled_reference_array(self):
        if self.labeled_reference_array is not None:
            return self.labeled_reference_array.astype(np.uint8)
        if self.reference_image_array is None:
            return None
        if self.project.configuration is None:
            return None

        img = self.reference_image_array
        if img.dtype == np.uint8:
            pass
        elif img.dtype == np.uint16:
            if np.amax(img) > 255:
                return
            img = (img >> 8).astype(np.uint8)
        else:
            return None

        table = self.project.configuration.color_data.table
        color_table = np.array(table, dtype=np.uint8)
        out = label_img_fastest(img, color_table).astype(np.uint8)
        self.labeled_reference_array = out
        return out

    @Slot()
    def dialog_for_reference_image(self) -> str | None:
        dialog = ReadOnlyImageFileDialog(self, "Select a dust filter", str(Path.home()))
        if not dialog.exec():
            # no file selected
            print("no file selected")
            return None
        files = dialog.selectedFiles()
        if len(files) == 0:
            print("0 file provided ??")
            # impossible put who knows
            return None
        file = files[0]
        return file

    def set_reference_image(self, img: NDArray):
        self.set_reference_image_array(img)
        self.set_reference_image_paintable(img)

    def set_reference_image_array(self, array: NDArray):
        self.reference_image_array: NDArray | None = array

    def set_reference_image_paintable(self, array: NDArray):
        if array.dtype == np.uint16:
            new_array = (array >> 8).astype(np.uint8)
        else:
            new_array = array
        self.reference_image_paintable = QImage(
            new_array.data,
            new_array.shape[1],
            new_array.shape[0],
            QImage.Format.Format_BGR888,
        )

    def set_palettized_reference(self, array: NDArray):
        self.set_palettized_reference_array(array)
        self.set_palettized_reference_paintable(array)

    def set_palettized_reference_array(self, array: NDArray):
        self.palettized_reference_array = array

    def set_palettized_reference_paintable(self, array: NDArray):
        if array.dtype == np.uint16:
            new_array = (array >> 8).astype(np.uint8)
        else:
            new_array = array
        self.palettized_reference_paintable = QImage(
            new_array.data,
            new_array.shape[1],
            new_array.shape[0],
            QImage.Format.Format_BGR888,
        )

    def start_kmeans_dialog(self):
        if self.reference_image_array is None:
            box = QMessageBox(self)
            box.setWindowTitle("Error: missing reference image")
            box.setText(
                "You tried to compute the k-means without reference image "
                "first. Please set a reference image first then try again."
            )
            box.exec()
            return
        dialog = KMeansDialog(self)
        if not dialog.exec():
            return
        thread = KmeansProcessor(self.reference_image_array, dialog.get_value(), self)
        thread.result_ready.connect(self.handle_kmeans_output)
        thread.finished.connect(thread.deleteLater)
        thread.run()
        # TODO: Reset Highlight

    @Slot(object)
    def handle_kmeans_output(self, output: tuple[NDArray, NDArray, NDArray]):
        # Called after start_kmeans_dialog
        # set color table
        self.set_palettized_reference(output[1])
        self.labeled_reference_array = (
            output[2]
            .reshape(self.palettized_reference_array.shape[0:2])  # type:ignore
            .astype(np.uint8)
        )
        if output[0].dtype == np.uint16:
            processed_output = (output[0] >> 8).astype(np.uint8)
        else:
            processed_output = output[0]
        listified = [list(row) + [0] for row in processed_output]
        self.project.set_lut(listified)
        self.palette_list.set_palette(listified)
        paintable = self.palettized_reference_paintable
        if paintable is not None:
            self.viewer.set_palettized_reference(paintable)
            self.viewer.show_palettized_reference()
            self.viewer.reset_highlight()

    def compute_count(self):
        # check for existence of an image directory
        img_directory = Path()  # <== TODO: Complete this
        if not img_directory.is_dir():
            # Should not happen but just in case:
            #   Stop this and querry the user for a valid
            #   directory of images
            return

    def select_reference_image(self):
        img_path: str | None = self.dialog_for_reference_image()
        if img_path is None:
            print("image path is None :(")
            return
        try:
            img = self.validate_reference_image(img_path)
        except InvalidFormatError as e:
            box = QMessageBox(self)
            box.setWindowTitle("Error: Invalid Format")
            channels = e.format_info[1]
            if channels != 3:
                box.setText(
                    f"The image you selected is invalid as it has {channels}"
                    " color channel(s) and 3 were expected (RGB)."
                )
            else:
                box.setText(
                    "The image you selected is invalid because the pixel"
                    " values are not coded on 8 or 16 bits"
                )
            box.exec()
            return
        except InvalidNameError:
            box = QMessageBox(self)
            box.setWindowTitle("Error: Invalid Name")
            box.setText(
                "The selected Image is invalid as the filename starts with"
                "a '.'. Files with such a name are hidden files that "
                "should be treated with special care."
            )
            box.exec()
            return
        except FailedOpeningError:
            box = QMessageBox(self)
            box.setWindowTitle("Error: Invalid File Type")
            box.setText(
                "The selected image could not be opened. Maybe you lack the"
                "necessary codecs to read it, the file extension is incorrect,"
                " or the file is corrupted. Please try again with a different "
                "file."
            )
            box.exec()
            return
        print("valid image :)")
        self.project.set_reference_image_path(img_path)
        self.set_reference_image(img)
        self.reset_kmeans()
        self.viewer.set_reference_image(
            self.reference_image_paintable
        )  # QImage as argument
        self.viewer.show_reference_image()

    def reset_kmeans(self):
        self.labeled_reference_array = None
        self.reset_palettized()

    def reset_palettized(self):
        self.palettized_reference_array = None
        self.palettized_reference_paintable = None
        self.viewer.reset_palettized()
        self.reset_highlight()

    def reset_highlight(self):
        self.viewer.reset_highlight()

    def validate_reference_image(self, path: str) -> NDArray:
        if Path(path).name.startswith("."):
            raise InvalidNameError(path)
        img = cv2.imread(path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        if img is None:
            raise FailedOpeningError(path)
        shape = img.shape
        if len(shape) < 3:
            channels = 1
        else:
            channels = img.shape[2]
        match img.dtype:
            case np.uint8:
                datatype = "uint8"
            case np.uint16:
                datatype = "uint16"
            case np.float32:
                datatype = "float32"
            case _:
                datatype = "other"
        if datatype not in ["uint8", "uint16"] or channels != 3:
            raise InvalidFormatError((datatype, channels), path)
        return img

    def show_palettized(self):
        if self.reference_image_array is None:
            # Error Message: No reference image
            box = QMessageBox(self)
            box.setWindowTitle("Error: missing reference image")
            box.setText(
                "You tried to show a palettized version of the reference image"
                " without a reference image in the first place. Please set a "
                "reference image first, compute it's k-means, then try again."
            )
            box.exec()
            return
        if self.palettized_reference_array is None:
            box = QMessageBox(self)
            box.setWindowTitle("Error: missing k-means")
            box.setText(
                "You tried to show a palettized version of the reference image"
                " without computing the k-means. Please compute the reference "
                "image's k-means, then try again."
            )
            box.exec()
            return
        if self.palettized_reference_paintable is None:
            ...
        if self.viewer.palettized_reference is None:
            self.viewer.set_palettized_reference(self.palettized_reference_paintable)
        self.viewer.show_palettized_reference()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(Project.from_path("test_file"))
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
