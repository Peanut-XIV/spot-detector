import random
import sys
import time

from PySide6.QtCore import QAbstractItemModel, QModelIndex, QObject, QThread, Slot
from PySide6.QtWidgets import QApplication

from spot_detector.view.main_window import MainWindow

def load(steps: int) -> None:
        print("Initialisation:")
        for i in range(steps + 1):
            time.sleep(random.random()/(steps / 4))
            val = 100 * i / steps
            print(f"\r{val:.2f}% [" + i * "|" + (steps - i) * " " + "]", end="")
        print("\nLoading finished")


class Controller(QObject):
    def __init__(self, window, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self.current_config_file = None
        self.current_image_file = None
        self.current_image_directory = None

        self.create_actions()
        self.bind_to_window()

    def bind_to_window(self):
        ...

    def create_actions(self):
        ...


if __name__ == "__main__":
    app = QApplication()
    main_window = MainWindow()
    controller = Controller(main_window)
    worker_thread = QThread()
    controller.moveToThread(worker_thread)
    main_window.show()
    sys.exit(app.exec())
