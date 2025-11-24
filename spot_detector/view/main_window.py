from pathlib import Path
import sys

from numpy.typing import NDArray

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QSplitter, QMessageBox
from PySide6.QtGui import QAction, QIcon

from spot_detector import rc_resources, rc_icons  # WARN: Do not remove
from spot_detector.model.models import Shade
from spot_detector.model.project import Project
from spot_detector.model.reference_image import ReferenceImageModel
from spot_detector.view.kmeans_dialog import KMeansDialog, KmeansProcessor
from spot_detector.view.palette_widget import Palette_List
from spot_detector.view.dialogs import (
    ConfirmOverwriteDialog,
    ReadOnlyImageFileDialog,
    SaveProjectAsDialog,
)
from spot_detector.view.image_viewer import (
    ViewerWidget,
    need_labels_msg,
    need_ref_image_msg,
)
from spot_detector.errors import (
    FailedOpeningError,
    InvalidFormatError,
    InvalidNameError,
)


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

        # could belong in an "AppState" object of some kind
        self.previous_rows = None  # The rows previously selected for highlight

    def _create_palette(self, parent):
        """
        A function for populating a palette widget with the projects shades.
        """
        self.palette_list = Palette_List(self.project.configuration.shades, parent)

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

    def _create_detection_settings_action(self):
        action = QAction("Detection Settings", self)
        action.triggered.connect(self.start_settings_window)

    def _create_viewer(self, parent):
        self.viewer = ViewerWidget(self.project, parent)
        self.viewer.request_palettized.connect(self.show_palettized_ref)
        self.viewer.request_highlight.connect(self.make_highlight)

    @Slot()
    def start_settings_window(self): ...

    @Slot()
    def make_highlight(self):
        rows = self.palette_list.selected_rows()
        if rows == self.previous_rows:
            self.viewer.show_highlight()
            return

        if self.project.reference_image_model is None:
            need_ref_image_msg(self)
            return

        if self.project.reference_image_model.mats.labeled_mat is None:
            need_labels_msg(self)
            return

        # could error if labeled_mat was set to None in the meantime
        self.project.reference_image_model.mats.highlight_selection(
            rows, self.project.configuration.shades
        )
        self.viewer.update_highlight()
        self.viewer.show_highlight()

    @Slot()
    def show_palettized_ref(self):
        if self.project.reference_image_model is None:
            need_ref_image_msg(self)
            return
        if self.project.reference_image_model.mats.labeled_mat is None:
            need_labels_msg(self)
            return

        self.viewer.update_palettized(msg_on_fail=False)
        self.viewer.update_highlight(msg_on_fail=False)
        self.viewer.show_palettized_reference()

    @Slot()
    def make_palettized_ref(self):
        if self.project.reference_image_model is None:
            need_ref_image_msg(self)
            return
        self.project.reference_image_model.mats.palettize_and_label_reference_from_shades(
            self.project.configuration.shades, do_update_highlight=True
        )
        self.viewer.update_palettized(msg_on_fail=False)
        self.viewer.update_highlight(msg_on_fail=False)
        self.viewer.show_palettized_reference()

    @Slot()
    def dialog_save_project_as(self):
        dialog = SaveProjectAsDialog()
        if not dialog.exec():
            return
        save_pathes = dialog.selectedFiles()
        if len(save_pathes) == 0:
            msg = QMessageBox(self)
            msg.setText(" selected")
            msg.exec()
            return
        path = Path(save_pathes[0])
        if path.exists():
            conf_diag = ConfirmOverwriteDialog(path, self)
            if conf_diag.exec() == QDialog.DialogCode.Rejected:
                return

        # NOTE: Could be a method of the project
        try:
            self.project.save_as(str(path))
        except OSError as e:
            box = QMessageBox(self)
            box.setWindowTitle("File Error")
            box.setText(
                f"An error occured while trying to save the project to the "
                f"following path: {str(path)}. Please ensure the path is valid"
                f" and that you have the permissions required to save a file "
                f"at the given path. Error type: {e}."
            )

    def dialog_for_reference_image(self) -> str | int:
        dialog = ReadOnlyImageFileDialog(
            self, "Select a reference image", str(Path.home())
        )
        if not dialog.exec():
            # no file selected
            print("no file selected")
            return 0
        files = dialog.selectedFiles()
        if len(files) == 0:
            print("0 file provided ??")
            # impossible put who knows
            return 0
        elif len(files) > 1:
            print("more than one file selected")
            return len(files)
        file = files[0]
        return file

    def start_kmeans_dialog(self):
        if self.project.reference_image_model is None:
            need_ref_image_msg(self)
            return

        dialog = KMeansDialog(self)
        if not dialog.exec():
            return

        thread = KmeansProcessor(
            self.project.reference_image_model.mats.reference.raw_mat,
            dialog.get_value(),
            self,
        )

        thread.result_ready.connect(self.handle_kmeans_output)
        thread.finished.connect(thread.deleteLater)
        thread.run()

    @Slot(object)
    def handle_kmeans_output(self, output: tuple[NDArray, NDArray, NDArray]):
        """
        called after computing the k-means

        sets the colortable and updates the `reference_image_model` as well as the viewer

        should not be called if the ref image is not set yet
        """

        assert self.project.reference_image_model is not None

        self.project.reference_image_model.mats.load_kmeans_result(output)

        self.viewer.update_palettized(msg_on_fail=False)
        self.viewer.show_palettized_reference()

        lut = output[0]
        shades = [Shade.from_pix(tuple(row[0:3])) for row in lut]
        self.project.set_shades(lut)
        self.palette_list.set_palette(shades)

    # TODO: create the function
    # 1 - Validate source path
    #   a - source path is not None
    #   b - source path is a directory
    #   c - correct internal structure
    #   d - correct file types
    #   e - (bonus) naming scheme?
    # 2 - Validate dest path
    #   a - dest path not None
    #   b - parent dir exists
    #   c - overwrite / no-overwrite
    #   d - resume previous compute?
    # 3 - Validate counting parameters
    #   a - labels count vs nbr of diff settings
    # 4 - Compute
    #   a - create loading screen
    #        - count processed images
    #        - give/update ETA
    #        - pause/resume Calculation controls
    #   b - prepare computation
    #        - create pipes
    #        - create threads
    #        - create writer thread
    #   d - start
    def compute_count(self): ...

    def select_reference_image(self):
        img_path: str | int = self.dialog_for_reference_image()
        if isinstance(img_path, int):
            if img_path == 0:
                print("no image selected")
            else:
                box = QMessageBox(self)
                box.setWindowTitle("Error: too many files selected")
                box.setText(
                    "Spot-detector can only handle one reference image at a "
                    "time. Please try again and select only one image."
                )
            return
        try:
            if self.project.reference_image_model is None:
                self.project.reference_image_model = ReferenceImageModel(path=img_path)
            else:
                self.project.reference_image_model.set_path(img_path)
        except InvalidFormatError as e:
            box = QMessageBox(self)
            box.setWindowTitle("Error: Invalid Format")
            box.setText(f"The format of the provided image is not supported. {e}")
            box.exec()
            return
        except InvalidNameError:
            box = QMessageBox(self)
            box.setWindowTitle("Error: Invalid Name")
            box.setText(
                "The selected Image is invalid as the filename starts with"
                "a '.'. Files and directories with such a name are hidden and "
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

        self.viewer.update_reference(False)
        self.viewer.show_reference_image()

    def show_palettized(self):
        img_model = self.project.reference_image_model
        if img_model is None:
            need_ref_image_msg(self)
            return

        if img_model.mats.labeled_mat is None:
            need_labels_msg(self)
            return

        if img_model.mats.palettized is None:
            # should not be possible
            palette = [shade.as_row() for shade in self.project.configuration.shades]
            palettized = img_model.mats.apply_color_list(palette)
            img_model.mats.update_palettized(palettized)
            self.viewer.update_palettized()

        self.viewer.show_palettized_reference()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(Project.from_path("test_file"))
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
