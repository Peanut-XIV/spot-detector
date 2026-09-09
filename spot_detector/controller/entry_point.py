import sys

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QApplication

from spot_detector.controller.start_manager_interface import StartManagerInterface
from spot_detector.view.main_window import MainWindow
from spot_detector.view.welcome_window import WelcomeWindow


class AppStartManager(QObject, StartManagerInterface):
    """
    An object responsible for starting
    the main window once a valid project
    is selected in the welcome window.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # TODO: Update listed projects on startup: For each file, check for presence on drive

    def start_from_welcome(self):
        # create welcome window
        self.welcome_window = WelcomeWindow(self)
        self.welcome_window.show()

    @Slot(object)
    def start_main_window(self, project):
        self.project = project
        self.main_window = MainWindow(project)
        self.main_window.show()


if __name__ == "__main__":
    app = QApplication()
    app.setApplicationName("Spot Detector")
    app.setApplicationDisplayName("Spot Detector")
    start_manager = AppStartManager()
    start_manager.start_from_welcome()
    sys.exit(app.exec())
