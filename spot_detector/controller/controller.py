import random
import sys
import time
from enum import IntEnum

from PySide6.QtCore import QObject, QThread, Slot, Signal
from PySide6.QtWidgets import QApplication

from spot_detector.view.main_window import MainWindow
from spot_detector.view.welcome_window import WelcomeWindow
from spot_detector.model.project import Project


class AppState(IntEnum):
    Welcome = 0
    Main = 1


def load(steps: int) -> None:
    print("Initialisation:")
    for i in range(steps + 1):
        time.sleep(random.random() / (steps / 4))
        val = 100 * i / steps
        print(f"\r{val:.2f}% [" + i * "|" + (steps - i) * " " + "]", end="")
    print("\nLoading finished")


class Controller(QObject):
    start_project_error: Signal = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.is_main_window_started: bool = False

    def start_from_welcome(self):
        # create welcome window
        self.welcome_window = WelcomeWindow(self)
        self.welcome_window.show()

    @Slot(Project)
    def check_project_and_start(self, project: Project):
        # This is where validation is done
        errors = project.check_fields()
        if errors is None:
            self.project = project
            # tell welcome window to hide
        else:
            self.start_project_error.emit(errors)


if __name__ == "__main__":
    app = QApplication()
    load(100)
    controller = Controller()
    worker_thread = QThread()
    controller.moveToThread(worker_thread)
    sys.exit(app.exec())
