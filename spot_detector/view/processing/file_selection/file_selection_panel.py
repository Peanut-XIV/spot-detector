from collections.abc import Sequence, Callable
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QModelIndex, Qt, Slot

import cv2 as cv
from numpy import uint8
from numpy.typing import NDArray

from spot_detector.file_utils import VALID_IMAGE_MIME_TYPES
from spot_detector.misc import canonical_path
from spot_detector.model.processing_settings_models import CroppingSettings, UserSelectedDir
from spot_detector.view.processing.file_selection.file_selection_model import FileSelectionModel
from spot_detector.view.processing.file_selection.file_selection_items import DirFilesPair, StatusUpdate
from spot_detector.processing.image_validation.checks import check_file_access, make_autocropping_checker, make_dust_filter_compat_checker, weird_tee
from spot_detector.view.processing.settings.crop_preview import ImageListPreview

class FileSelectionWidget(QWidget):
    def __init__(
        self,
        model: FileSelectionModel,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self._init_layout()
        _ = model.file_count_changed.connect(self.refresh_filecount)

        self._list_view.setModel(model)
        self._list_view.setTextElideMode(Qt.TextElideMode.ElideMiddle)

    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)

        self._list_view: QTreeView = QTreeView(self)
        self._list_view.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list_view)

        button_layout_1 = QHBoxLayout()
        button_layout_1.setContentsMargins(0,0,0,0)

        self.addfiles_button: QPushButton = QPushButton("Add Files", self)
        button_layout_1.addWidget(self.addfiles_button)

        self.adddir_button: QPushButton = QPushButton("Add Directory", self)
        button_layout_1.addWidget(self.adddir_button)

        self.removefile_button: QPushButton = QPushButton("Remove", self)
        button_layout_1.addWidget(self.removefile_button)

        layout.addLayout(button_layout_1)

        button_layout_2 = QHBoxLayout()
        button_layout_2.setContentsMargins(0,0,0,0)

        self._filecount_label: QLabel = QLabel("Total Files: 0", self)
        button_layout_2.addWidget(self._filecount_label)

        self.check_button: QPushButton = QPushButton("Check Files", self)
        button_layout_2.addWidget(self.check_button)

        layout.addLayout(button_layout_2)

    def preset_column_width(self):
        list_size = self._list_view.width()
        X = (list_size - 100) / 4
        name_width = int(max(80, X))
        path_width = int(max(240, 3*X))
        count_width = 40
        status_width = 40

        self._list_view.setColumnWidth(0, name_width)
        self._list_view.setColumnWidth(1, path_width)
        self._list_view.setColumnWidth(2, count_width)
        self._list_view.setColumnWidth(3, status_width)

    def get_selection(self) -> list[QModelIndex]:
        return self._list_view.selectedIndexes()

    @Slot(int)
    def refresh_filecount(self, count: int):
        self._filecount_label.setText(f"Total Files: {count}")

    @Slot()
    def remove_highighted_items(self) -> None:
        selection = self._list_view.selectedIndexes()
        model = self._list_view.model()
        if not isinstance(model, FileSelectionModel):
            return
        model.remove_indexes(selection)

    @Slot(object)
    def check_highlighted_items(self, check_function: Callable[[Path], StatusUpdate]):
        selection = self.get_selection()
        model = self._list_view.model()
        if not isinstance(model, FileSelectionModel):
            return
        model.check_entries(selection, check_function)

class ErrorFeedbackBox(QWidget):

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self._init_layout()

        _ = self._clear_button.clicked.connect(self.clear_messages)


    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)

        top_line_layout = QHBoxLayout()

        self._error_count_label: QLabel = QLabel("0 Error message", self)
        top_line_layout.addWidget(self._error_count_label)
        top_line_layout.addStretch()
        self._clear_button: QPushButton = QPushButton("Clear Messages", self)
        top_line_layout.addWidget(self._clear_button)
        layout.addLayout(top_line_layout)

        self._error_list: QListWidget = QListWidget(self)
        layout.addWidget(self._error_list)

    @Slot()
    def clear_messages(self):
        self._error_list.clear()
        self.update_count_label()

    @Slot(list)
    def append_messages(self, messages: list[str]):
        for msg in messages:
            _ = QListWidgetItem(msg, self._error_list)
        self.update_count_label()

    def update_count_label(self):
        error_count = self._error_list.count()
        if error_count == 0:
            self._error_count_label.setText("0 Error message")
        elif error_count == 1:
            self._error_count_label.setText("1 Error message")
        else:
            self._error_count_label.setText(f"{error_count} Error messages")


class FileSelectionPanel(QWidget):

    def __init__(
        self,
        previous_directory: Path | None = None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self.setMinimumSize(400, 500)
        self.setBaseSize(400, 600)

        self._previous_directory: Path
        if previous_directory is None:
            self._previous_directory = Path.home()
        else:
            self._previous_directory = previous_directory

        self._model: FileSelectionModel = FileSelectionModel()

        self._init_layout()

        _ = self._list_widget.addfiles_button.clicked.connect(self.query_user_for_files)
        _ = self._list_widget.adddir_button.clicked.connect(self.query_user_for_directory)
        _ = self._list_widget.removefile_button.clicked.connect(self._list_widget.remove_highighted_items)
        _ = self._list_widget.check_button.clicked.connect(self.check_all_files_for_access)
        _ = self._model.new_error_messages.connect(self._feedback_box.append_messages)

        self._list_widget.preset_column_width()


    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        panel_title = QLabel("File Selection")
        panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(panel_title)

        self._list_widget: FileSelectionWidget = FileSelectionWidget(self._model)
        layout.addWidget(self._list_widget, 2)

        self._feedback_box: ErrorFeedbackBox = ErrorFeedbackBox(self)
        layout.addWidget(self._feedback_box, 1)

    def load_entries_from_pairs(self, pairs: Sequence[tuple[Path|None, list[Path]]]):
        self._model.load_entries_from_pairs(pairs)

    def get_entries_as_pairs(self) -> Sequence[DirFilesPair]:
        return self._model.get_entries_as_pairs()

    @Slot()
    def query_user_for_files(self) -> None:
        dialog = QFileDialog(self)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        dialog.setDirectory(str(self._previous_directory))
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setWindowTitle("Select files to process")
        dialog.setMimeTypeFilters(["application/octet-stream"] + VALID_IMAGE_MIME_TYPES)
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Add Selection")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Cancel")

        if not dialog.exec():
            return

        add_list: list[Path] = []
        for file in dialog.selectedFiles():
            fp = canonical_path(file)
            if fp.exists() and fp.is_file():
                add_list.append(fp)
        _ = self._model.add_file_entries(add_list, QModelIndex())

        self._previous_directory = canonical_path(dialog.selectedFiles()[0]).parent

    @Slot()
    def query_user_for_directory(self) -> None:
        dialog = QFileDialog(self)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        dialog.setDirectory(str(self._previous_directory))
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setWindowTitle("Select directory of files to process")
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Add Directory")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Cancel")

        if not dialog.exec():
            return

        for directory in dialog.selectedFiles():
            dp = canonical_path(directory)
            if dp.exists() and dp.is_dir():
                files = [e for e in dp.iterdir() if e.is_file()]
                _ = self._model.add_directory_and_content(dp, files)

        self._previous_directory = canonical_path(dialog.selectedFiles()[0]).parent


    @Slot()
    def check_all_files_for_access(self) -> None:
        self._model.check_all(check_file_access)

    @Slot(str)
    def check_all_files_for_filter_compat(self, filter_path: str) -> None:
        print("checking filter compat")
        mat = cv.imread(filter_path, cv.IMREAD_COLOR_BGR | cv.IMREAD_ANYDEPTH)
        if mat is None:
            text = "the provided path failed to parse to a valid image"
            message = QMessageBox(self, text=text)
            _ = message.exec()
            return
        shape = list(mat.shape)  # pyright: ignore[reportAny]
        data_type = mat.dtype

        compat_checker = make_dust_filter_compat_checker(shape, data_type)

        self._model.check_all(compat_checker)


    @Slot(CroppingSettings)
    def check_selection_for_cropping(self, parameters: CroppingSettings) -> None:
        check_function = weird_tee(make_autocropping_checker(parameters))
        selection = self._list_widget.get_selection()
        mat_list: list[tuple[Path, NDArray[uint8] | None]] = []

        for index in selection:
            if res := self._model.check_entry_2(index, check_function):
                print(f"adding {str(res[0])}")
                mat_list.append(res)

        crop_preview_dialog = ImageListPreview(mat_list, self)
        crop_preview_dialog.show()




    def get_model(self) -> list[str | UserSelectedDir]:
        model: list[str | UserSelectedDir] = []
        pairs = self.get_entries_as_pairs()
        for dir, entries in pairs:
            path_strings = [str(path) for path in entries]
            if dir is None:
                model += path_strings
            else:
                model.append(UserSelectedDir(path=str(dir), files=path_strings))

        return model

    @Slot(list)
    def set_model(self, model: list[str | UserSelectedDir]) -> None:
        files = [Path(item) for item in model if isinstance(item, str)]
        dirs = [item for item in model if isinstance(item, UserSelectedDir)]

        pairs: list[DirFilesPair] = []
        pairs.append((None, files))
        for dir in dirs:
            path = Path(dir.path)
            files = [Path(file) for file in dir.files]
            pairs.append((path, files))

        self.load_entries_from_pairs(pairs)



if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = FileSelectionPanel()
    window.show()

    sys.exit(app.exec())
