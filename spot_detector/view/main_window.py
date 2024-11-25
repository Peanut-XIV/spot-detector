import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
)

from spot_detector.view.image_viewer import ViewerWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spot Detector GUI")
        # self._create_menu()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.viewer)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        self.setCentralWidget(splitter)

    # TODO: refactor to create actions in controller and add them later...
    # def _create_menu(self):
    #     self.menu = self.menuBar()
    #     self._file_menu = self.menu.addMenu("File")
    #     self._file_menu.addAction("Quit", self.close, "Ctrl+Q")
    #     self._file_menu.addAction("Load Image", self._load_image_with_dialog, "Ctrl+I")
    #     self._file_menu.addAction("Load Configuration", self._load_config_with_dialog, "Ctrl+L")
    #     self._file_menu.addAction("New Configuration", self._new_configuration_dialog, "Ctrl+N")

    def _create_viewer(self, parent):
        self.viewer = ViewerWidget(parent)

    def _load_image_with_dialog(self):
        print("A File dialog box appears")
        ...

    def _load_config_with_dialog(self):
        print("A File dialog box appears")
        ...

    def _new_configuration_dialog(self):
        print("Would you like to save th current configuration file before closing ?")
        ...


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
