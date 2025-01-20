import sys
from pathlib import Path
import json
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)
from PySide6.QtCore import (
    QSize,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QPixmap,
)

from spot_detector.view.new_project_dialog import NewProjectDialog


class WelcomeWindow(QWidget):
    start_project: Signal = Signal(dict)

    def __init__(self, controller) -> None:
        super().__init__(None, Qt.WindowType.Window)
        # Load previous projects
        self.controller = controller
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

    def fetch_recent_projects(self) -> list[str]:
        recent_projects_fp = Path.home() / ".spot_detector" / "recent_projects.txt"
        with open(recent_projects_fp, "r", encoding="UTF-8") as recent_proj_file:
            projects = [
                line for line in recent_proj_file if self.is_valid_project_path(line)
            ]
        return projects

    def is_valid_project_path(self, path: str) -> bool:
        path_obj = Path(path)
        output = (
            (not path.startswith("#"))
            and path_obj.exists()
            and path_obj.is_file()
            and path_obj.suffix == ".spot"  # Actually a json file but *hush*
        )
        return output

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

    @Slot()
    def create_new_project(self):
        dialog = NewProjectDialog(self.controller, self)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WelcomeWindow(None)
    window.show()
    sys.exit(app.exec())
