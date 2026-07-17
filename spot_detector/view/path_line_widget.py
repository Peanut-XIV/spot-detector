from enum import Enum
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QWidget, QLineEdit, QPushButton
from PySide6.QtCore import Slot

from spot_detector.file_utils import VALID_CSV_TYPES, VALID_IMAGE_TYPES
from spot_detector.view.dialogs.dialogs import (
    OpenDirFileDialog,
    ReadOnlyImageFileDialog,
    SaveProcessingFileDialog,
)

class PathType(Enum):
    ReadOnlyImage = 0
    Directory = 1
    AnyCSV = 2
    Other = 3

class PathEdit(QLineEdit):
    def __init__(
        self,
        path_type: PathType,
        caption: str = "",
        starting_path: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.starting_path: Path

        if starting_path is None:
            self.starting_path = Path.home()
        elif isinstance(starting_path, Path):
            self.starting_path = starting_path
        else:
            self.starting_path = Path(starting_path)

        self.caption:        str = caption
        self.path_type: PathType = path_type
        self.dialog: QFileDialog

        match self.path_type:

            case PathType.ReadOnlyImage:
                filter = "Valid Image Types " + VALID_IMAGE_TYPES
                self.dialog = ReadOnlyImageFileDialog(self, self.caption, str(self.starting_path), filter)

            case PathType.Directory:
                self.dialog = OpenDirFileDialog(self, self.caption, str(self.starting_path))

            case PathType.AnyCSV:
                filter = "Valid File Types " + VALID_CSV_TYPES
                self.dialog = SaveProcessingFileDialog(self, self.caption, str(self.starting_path), filter)

            case PathType.Other:
                self.dialog = QFileDialog(self, self.caption, str(self.starting_path))

        self.explore_button: QPushButton = QPushButton("Explore", parent)
        _ = self.explore_button.clicked.connect(self.explore)

    def set_starting_path(self, path: str | Path):
        if isinstance(path, str):
            self.starting_path = Path(path)
        else:
            self.starting_path = path

    def get_button(self) -> QPushButton:
        return self.explore_button

    @Slot()
    def explore(self):
        self.dialog.setDirectory(str(self.starting_path))
        if not self.dialog.exec():
            return

        files = self.dialog.selectedFiles()

        if len(files) > 0:
            self.setText(files[0])

            self.starting_path = Path(files[0]).parent
