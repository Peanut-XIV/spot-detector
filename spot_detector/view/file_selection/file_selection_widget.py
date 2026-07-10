from collections.abc import Sequence
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QFrame
)
from PySide6.QtCore import QModelIndex, Qt, Slot

from spot_detector.file_utils import VALID_IMAGE_MIME_TYPES
from spot_detector.view.file_selection.file_selection_model import FileSelectionModel
from spot_detector.view.file_selection.file_selection_items import DirFilesPair
from spot_detector.view.processing.checks import check_file_access

class FileSelectionWidget(QWidget):
    def __init__(
        self,
        model: FileSelectionModel,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self._init_layout()
        self.setMinimumSize(200, 100)
        self.setBaseSize(500, 500)
        self.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.Expanding, # Horizontal
                QSizePolicy.Policy.Expanding, #   Vertical
                type=QSizePolicy.ControlType.Frame
            )
        )
        _ = model.file_count_changed.connect(self.refresh_filecount)

        view = self._list_view
        view.setColumnWidth(0, 100)
        view.setColumnWidth(1, 300)
        view.setColumnWidth(2, 50)
        view.setColumnWidth(3, 50)
        view.setModel(model)
        view.setTextElideMode(Qt.TextElideMode.ElideMiddle)

    def _init_layout(self):
        layout = QVBoxLayout(self)

        self._list_view: QTreeView = QTreeView(self)
        self.setMinimumSize(400, 100)
        self._list_view.setSizeAdjustPolicy(QTreeView.SizeAdjustPolicy.AdjustToContents)
        self._list_view.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self._list_view.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list_view)

        button_layout = QHBoxLayout()

        self.addfiles_button: QPushButton = QPushButton("Add Files", self)
        button_layout.addWidget(self.addfiles_button)

        self.adddir_button: QPushButton = QPushButton("Add Directory", self)
        button_layout.addWidget(self.adddir_button)

        self.removefile_button: QPushButton = QPushButton("Remove", self)
        button_layout.addWidget(self.removefile_button)

        button_layout.addStretch()

        self._filecount_label: QLabel = QLabel("Total Files: 0", self)
        button_layout.addWidget(self._filecount_label)

        button_layout.addStretch()

        self.check_button: QPushButton = QPushButton("Check Files", self)
        button_layout.addWidget(self.check_button)

        layout.addLayout(button_layout)

    @Slot(int)
    def refresh_filecount(self, count: int):
        self._filecount_label.setText(f"Total Files: {count}")

    @Slot()
    def remove_selection(self) -> None:
        selection = self._list_view.selectedIndexes()
        model = self._list_view.model()
        if not isinstance(model, FileSelectionModel):
            return
        model.remove_indexes(selection)

class ErrorFeedbackBox(QWidget):

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self._init_layout()
        self.setMinimumSize(200, 100)
        self.setBaseSize(500, 100)
        self.setSizePolicy(
                QSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
        )

        _ = self._clear_button.clicked.connect(self.clear_messages)


    def _init_layout(self):
        layout = QVBoxLayout(self)
        top_line_layout = QHBoxLayout()

        self._error_count_label: QLabel = QLabel("There is no error message currently", self)
        top_line_layout.addWidget(self._error_count_label)
        top_line_layout.addStretch()
        self._clear_button: QPushButton = QPushButton("Clear Messages", self)
        top_line_layout.addWidget(self._clear_button)
        layout.addLayout(top_line_layout)

        # self._error_list: QLabel = QLabel("")
        self._error_list: QListWidget = QListWidget(self)
        self._error_list.setFrameShape(QFrame.Shape.Panel)
        self._error_list.setFrameShadow(QFrame.Shadow.Sunken)
        self._error_list.setSizePolicy(
                QSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
        )
        layout.addWidget(self._error_list)

    @Slot()
    def clear_messages(self):
        self._error_list.clear()

    @Slot(list)
    def append_messages(self, messages: list[str]):
        for msg in messages:
            _ = QListWidgetItem(msg, self._error_list)
        self.update_count_label()

    def update_count_label(self):
        error_count = self._error_list.count()
        if error_count == 0:
            self._error_count_label.setText("There is no error message currently")
        elif error_count == 1:
            self._error_count_label.setText("1 Error message")
        else:
            self._error_count_label.setText(f"{error_count} Error messages")


class FileSelectionPanel(QWidget):

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self._prev_directory: Path = Path.home()
        self._model: FileSelectionModel = FileSelectionModel()

        self._init_layout()

        view = self._list_widget._list_view  # pyright: ignore[reportPrivateUsage]
        view.setColumnWidth(0, 100)
        view.setColumnWidth(1, 300)
        view.setColumnWidth(2, 50)
        view.setColumnWidth(3, 50)

        _ = self._list_widget.addfiles_button.clicked.connect(self.query_user_for_files)
        _ = self._list_widget.adddir_button.clicked.connect(self.query_user_for_directory)
        _ = self._list_widget.removefile_button.clicked.connect(self._list_widget.remove_selection)
        _ = self._list_widget.check_button.clicked.connect(self.check_all_files)
        _ = self._model.new_error_messages.connect(self._feedback_box.append_messages)


    def _init_layout(self):
        layout = QVBoxLayout(self)

        panel_title = QLabel("File Selection")
        panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(panel_title)

        self._list_widget: FileSelectionWidget = FileSelectionWidget(self._model)
        layout.addWidget(self._list_widget, 2)

        self._feedback_box: ErrorFeedbackBox = ErrorFeedbackBox(self)
        layout.addWidget(self._feedback_box, 1)

    def load_list(self, content: list[Path]):
        self._model.load_entries(content)

    def get_file_list(self) -> list[Path]:
        return self._model.get_file_list()

    def load_entries_from_pairs(self, pairs: Sequence[tuple[Path|None, list[Path]]]):
        self._model.load_entries_from_pairs(pairs)

    def get_entries_as_pairs(self) -> Sequence[DirFilesPair]:
        return self._model.get_entries_as_pairs()

    @Slot()
    def query_user_for_files(self) -> None:
        dialog = QFileDialog(self)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        dialog.setDirectory(str(self._prev_directory))
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
            fp = Path(file).resolve()
            if not (fp.exists() and not fp.is_dir() and fp.is_file()):
                pass
            add_list.append(fp)
        _ = self._model.add_file_entries(add_list, QModelIndex())

        self._prev_directory = Path(dialog.selectedFiles()[0]).resolve().parent

    @Slot()
    def query_user_for_directory(self) -> None:
        dialog = QFileDialog(self)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        dialog.setDirectory(str(self._prev_directory))
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setWindowTitle("Select directory of files to process")
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Add Directory")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Cancel")

        if not dialog.exec():
            return

        for directory in dialog.selectedFiles():
            dp = Path(directory).resolve()
            if not (dp.exists() and dp.is_dir()):
                pass
            files = [e for e in dp.iterdir() if e.is_file()]
            _ = self._model.add_directory_and_content(dp, files)

        self._prev_directory = Path(dialog.selectedFiles()[0]).resolve().parent


    @Slot()
    def check_all_files(self) -> None:
        self._model.check_all(check_file_access)

if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = FileSelectionPanel()
    window.show()

    sys.exit(app.exec())
