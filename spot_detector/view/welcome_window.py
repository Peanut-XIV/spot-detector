import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QPushButton,
)
from PySide6.QtCore import (
    QSize,
    Qt,
    Signal,
    Slot,
    QObject,
)
from pydantic import ValidationError

from spot_detector.controller.start_manager_interface import StartManagerInterface
from spot_detector.view.dialogs import OpenProjectDialog
from spot_detector.view.new_project_dialog import NewProjectDialog
from spot_detector.view.welcome_window_interface import WelcomeWindowInterface
from spot_detector.model.project import Project


class WelcomeWindow(QWidget, WelcomeWindowInterface):
    start_project: Signal = Signal(dict)

    def __init__(self, start_manager: QObject | None) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.start_manager = start_manager
        self.project: None | Project = None
        # layout
        layout = QHBoxLayout(self)
        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        self.left_panel = self._create_left_panel()
        splitter.addWidget(self.left_panel)
        self.right_panel = self._create_right_panel()
        splitter.addWidget(self.right_panel)
        layout.addWidget(splitter)
        self.setLayout(layout)
        self.setMinimumSize(QSize(500, 300))
        self.setMaximumSize(QSize(1000, 600))
        self.setWindowTitle("Welome to spot-detector!")

    def _create_left_panel(self) -> QWidget:
        panel = QWidget(self, Qt.WindowType.Widget)
        layout = QVBoxLayout()
        self.open_button = QPushButton("Open an existing project", panel)
        layout.addWidget(self.open_button)
        self.new_button = QPushButton("Create a new project", panel)
        self.new_button.clicked.connect(self.create_new_project)
        layout.addWidget(self.new_button)
        layout.addStretch(1)
        top_layout = QHBoxLayout(panel)
        top_layout.addLayout(layout)
        top_layout.addStretch(1)
        panel.setLayout(top_layout)
        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget(self, Qt.WindowType.Widget)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Recently opened projects", panel))
        self.recent_project_list = QListWidget(self)
        layout.addWidget(self.recent_project_list)
        layout.addStretch(1)
        layout_2 = QHBoxLayout(panel)
        layout_2.addStretch(1)
        self.open_recent_button = QPushButton("open", panel)
        layout_2.addWidget(self.open_recent_button)
        layout.addLayout(layout_2)
        panel.setLayout(layout)
        return panel

    @Slot(Project)
    def setProject(self, project: Project):
        self.project = project

    @Slot()
    def create_new_project(self):
        dialog = NewProjectDialog(self)
        dialog.exec()
        # Maybe the project should be an attribute of the dialog
        # and retrieved by the parent
        if self.project is not None:
            self.start_main_window_and_hide(self.project)

    def open_existing_project(self):
        dialog = OpenProjectDialog(self)
        if not dialog.exec():
            return
        project_file = dialog.selectedFiles()[0]
        project = None
        try:
            project = Project.from_path(project_file)
        except ValidationError:
            message = QMessageBox(parent=self)
            message.setText("The project file could not be opened.")
            message.setWindowTitle("Error")
            message.exec()
        if project is not None:
            self.start_main_window_and_hide(project)

    def start_main_window_and_hide(self, project: Project):
        manager = self.start_manager
        if isinstance(manager, StartManagerInterface):
            manager.start_main_window(project)
            self.close()
        else:
            message = QMessageBox(self)
            message.setText(
                "Could not create new project since the start manager is missing"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WelcomeWindow(None)
    window.show()
    sys.exit(app.exec())
