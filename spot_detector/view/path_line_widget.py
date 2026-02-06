from pathlib import Path
from typing import Literal
from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton
from PySide6.QtCore import Slot

from spot_detector.view.dialogs import OpenDirFileDialog, ReadOnlyImageFileDialog


class PathLineWidget(QLineEdit):
    def __init__(
        self,
        path_type: Literal["read_only_img", "dir", "any_csv", "other"],
        caption: str = "",
        starting_path: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if starting_path is not None:
            self.starting_path = starting_path
        else:
            self.starting_path = str(Path.home())

        self.caption = caption

        self.path_type = path_type
        if self.path_type == "read_only_img":
            self.dialog = ReadOnlyImageFileDialog(
                self, self.caption, self.starting_path
            )
        elif self.path_type == "dir":
            self.dialog = OpenDirFileDialog(self, self.caption, self.starting_path)
        elif self.path_type == "any_csv":
            self.dialog =
        else:
            self.dialog = 

        self.explore_button = QPushButton("Explore", parent)
        self.explore_button.clicked.connect(self.explore)

    def set_starting_path(self, path: str):
        self.starting_path = path

    def get_button(self) -> QPushButton:
        return self.explore_button

    @Slot()
    def explore(self):
        self.dialog.setDirectory(self.starting_path)
        if self.dialog.exec():
            files = self.dialog.selectedFiles()
            if len(files) > 0:
                self.setText(files[0])
