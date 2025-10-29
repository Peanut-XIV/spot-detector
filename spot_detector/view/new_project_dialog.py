import sys
from pathlib import Path
from typing import Literal
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QDialog,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import (
    Qt,
    Slot,
)
from pydantic import ValidationError

from spot_detector.model.project import Project
from spot_detector.view.dialogs import OpenDirFileDialog, ReadOnlyImageFileDialog
from spot_detector.view.welcome_window_interface import WelcomeWindowInterface


class NewProjectDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Dialog,
    ) -> None:
        super().__init__(parent, f)
        self.setWindowTitle("New project creation")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Fill in the fields to create a new project:", self))
        left_panel = self.create_left_panel()
        layout.addWidget(left_panel)
        layout.addStretch(1)
        layout_btm = QHBoxLayout(self)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        layout_btm.addWidget(self.cancel_button)
        layout_btm.addStretch(1)
        self.create_button = QPushButton("Create", self)
        self.create_button.setDefault(True)
        self.create_button.clicked.connect(self.attempt_create)
        layout_btm.addWidget(self.create_button)
        layout.addLayout(layout_btm)

        self.setLayout(layout)

    def create_left_panel(self):
        panel = QWidget(self)
        panel.setMinimumWidth(600)

        layout = QGridLayout(panel)
        l0 = QLabel("Name:", self)
        layout.addWidget(l0, 0, 0)
        layout.setAlignment(l0, Qt.AlignmentFlag.AlignRight)
        self.name_line = QLineEdit("Unnamed_project", self)
        layout.addWidget(self.name_line, 0, 1)

        l1 = QLabel("Dust Filter path:", self)
        self.dust_filter_field = PathLineWidget(
            "read_only_img", "Select a dust filter", None, self
        )
        layout.addWidget(l1, 1, 0)
        layout.setAlignment(l1, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.dust_filter_field, 1, 1)
        layout.addWidget(self.dust_filter_field.get_button(), 1, 2)

        l2 = QLabel("Reference image path:", self)
        self.ref_image_field = PathLineWidget(
            "read_only_img", "Select a reference image", None, self
        )
        layout.addWidget(l2, 2, 0)
        layout.setAlignment(l2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.ref_image_field, 2, 1)
        layout.addWidget(self.ref_image_field.get_button(), 2, 2)

        l3 = QLabel("Image directory path:", self)
        self.image_directory_field = PathLineWidget(
            "dir", "Select an image directory", None, self
        )
        layout.addWidget(l3, 3, 0)
        layout.setAlignment(l3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.image_directory_field, 3, 1)
        layout.addWidget(self.image_directory_field.get_button(), 3, 2)
        panel.setLayout(layout)
        return panel

    @Slot()
    def attempt_create(self):
        data = {
            "name": self.name_line.text(),
            "dust_filter_path": self.dust_filter_field.text(),
            "ref_image_path": self.ref_image_field.text(),
            "image_directory_path": self.image_directory_field.text(),
        }
        validation_success = True
        output = None
        error_text = "data is None"
        try:
            output = Project.from_dict(data)
        except ValidationError as e:
            # Error message
            validation_success = False
            error_text = str(e)

        if validation_success:
            parent = self.parent()
            if isinstance(parent, WelcomeWindowInterface) and output is not None:
                parent.setProject(output)  # type: ignore
                self.accept()
            else:
                message = QMessageBox(self)
                message.setText("Error: Parent of NewProjectDialog is not supported")
                message.exec()
        elif not validation_success or output is None:
            message = QMessageBox(self)
            message.setText("Error: the input data may not be valid:\n" + error_text)
            message.exec()
            # raise validation error message
            # don't close dialog


class PathLineWidget(QLineEdit):
    def __init__(
        self,
        path_type: Literal["read_only_img", "dir", "other"],
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

        self.setMinimumWidth(350)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    truc = NewProjectDialog(None)
    truc.show()
    sys.exit(app.exec())
