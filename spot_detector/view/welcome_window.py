import sys
from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from spot_detector.controller.start_manager_interface import StartManagerInterface
from spot_detector.file_utils import get_local_data_dir
from spot_detector.model.project import Project
from spot_detector.view.dialogs.dialogs import OpenProjectDialog
from spot_detector.view.new_project_dialog import NewProjectDialog
from spot_detector.view.welcome_window_interface import WelcomeWindowInterface


class WelcomeWindow(QWidget, WelcomeWindowInterface):
    start_project: Signal = Signal(dict)

    def __init__(self, start_manager: QObject | None) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.start_manager: QObject | None = start_manager
        self.project: Project | None = None
        self.open_button: QPushButton
        self.open_recent_button: QPushButton
        self.new_button: QPushButton
        self.recent_projects_list: QListWidget
        self.setObjectName("Welcome Window")

        # layout
        layout = QHBoxLayout(self)
        self.left_panel: QWidget = self._create_left_panel()
        layout.addWidget(self.left_panel)
        layout.addWidget(QFrame(self, frameShape=QFrame.Shape.VLine))
        self.right_panel: QWidget = self._create_right_panel()
        layout.addWidget(self.right_panel)
        self.setLayout(layout)

        _ = self.recent_projects_list.itemDoubleClicked.connect(self.on_doubleclick_recent)

        self.load_project_entries()

        # self.setMinimumSize(QSize(500, 300))
        # self.setMaximumSize(QSize(1000, 600))
        self.setWindowTitle("Welome to spot-detector!")

    def _create_left_panel(self) -> QWidget:
        panel = QWidget(self, Qt.WindowType.Widget)
        panel.setObjectName("left widget")
        layout = QVBoxLayout()
        layout.setObjectName("base")
        self.open_button = QPushButton("Open an existing project", panel)
        _ = self.open_button.clicked.connect(self.open_existing_project)
        layout.addWidget(self.open_button)
        self.new_button = QPushButton("Create a new project", panel)
        _ = self.new_button.clicked.connect(self.create_new_project)
        layout.addWidget(self.new_button)
        layout.addStretch(1)
        top_layout = QHBoxLayout()
        top_layout.setObjectName("top")
        top_layout.addLayout(layout)
        top_layout.addStretch(1)
        panel.setLayout(top_layout)
        panel.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget(self, Qt.WindowType.Widget)
        panel.setObjectName("right widget")
        layout = QVBoxLayout(panel)
        layout.setObjectName("base")
        layout.addWidget(QLabel("Recently opened projects", panel))
        list_widget = QListWidget(self)
        list_widget.setSelectionMode(list_widget.SelectionMode.SingleSelection)
        self.recent_projects_list = list_widget
        layout.addWidget(self.recent_projects_list)
        layout.addStretch(1)
        layout_2 = QHBoxLayout()
        layout_2.setObjectName("top")
        layout_2.addStretch(1)
        self.open_recent_button = QPushButton("open", panel)
        _ = self.open_recent_button.clicked.connect(self.open_selected_recent_project)
        layout_2.addWidget(self.open_recent_button)
        layout.addLayout(layout_2)
        panel.setLayout(layout)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setMinimumWidth(400)
        return panel

    def load_project_entries(self):
        projects_cache = get_local_data_dir() / "spot-detector" / "recent_projects.txt"

        if not projects_cache.exists():
            parent = projects_cache.parent
            if not parent.exists():
                parent.mkdir(parents=True)
            projects_cache.touch()

        with open(projects_cache, "r") as f:
            entries = [Path(line.strip("\n\r ")) for line in f]

        for project_path in entries:
            name = self.get_project_name(project_path)
            _ = RecentFileItem(project_path, name, self.recent_projects_list)


    def get_project_name(self, project_path: Path) -> str:
        if project_path.exists():
            try:
                project = Project.from_path(project_path)
                name = project.name
            except OSError:
                name = "[Failed Opening]"
            except ValidationError:
                name = "[Invalid JSON]"
            except Exception as other:  # noqa: BLE001
                print(f"unexpected error {other}")
                name = "[Error]"
            return name
        print("this path does not exist")
        print(str(project_path))
        return "[Not Found]"


    @Slot(Project)
    def setProject(self, project: Project):
        self.project = project

    @Slot()
    def create_new_project(self):
        dialog = NewProjectDialog(self)
        _ = dialog.exec()
        # Maybe the project should be an attribute of the dialog
        # and retrieved by the parent
        if self.project is not None:
            self.start_main_window_and_hide(self.project)


    def open_project(self, file_path: str | Path):
        try:
            project = Project.from_path(file_path)
        except ValidationError:
            message = QMessageBox(parent=self)
            message.setText("The project file could not be opened.")
            message.setWindowTitle("Error")
            _ = message.exec()
            project = None
        if project is not None:
            self.start_main_window_and_hide(project)


    def open_existing_project(self):
        dialog = OpenProjectDialog(self)
        if not dialog.exec():
            return
        project_file = dialog.selectedFiles()[0]
        self.open_project(project_file)


    def open_selected_recent_project(self):
        items = self.recent_projects_list.selectedItems()
        if len(items) != 1:
            return
        item = items[0]
        if isinstance(item, RecentFileItem):
            self.open_project(item.path)


    def on_doubleclick_recent(self, item: QListWidgetItem):
        if isinstance(item, RecentFileItem):
            self.open_project(item.path)


    def start_main_window_and_hide(self, project: Project):
        manager = self.start_manager
        if isinstance(manager, StartManagerInterface):
            manager.start_main_window(project)
            _ = self.close()
        else:
            message = QMessageBox(self)
            message.setText(
                "Could not create new project since the start manager is missing"
            )



class RecentFileItem(QListWidgetItem):
    def __init__(self, file_path: str | Path, project_name: str, listview: QListWidget):
        super().__init__(f"{project_name}\n{file_path!s}", listview)
        self.path: Path = Path(file_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WelcomeWindow(None)
    window.show()
    sys.exit(app.exec())
