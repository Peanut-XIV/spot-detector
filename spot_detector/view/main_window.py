import sys
import spot_detector.resources
from importlib.resources import files
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QLabel,
    QPushButton,
    QGroupBox,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spot Detector GUI")

        self._create_settings_panel()
        self._create_image_panel()
        self._create_menu()

        layout = QHBoxLayout()
        layout.addWidget(self._settings_panel)
        layout.addWidget(self._image_panel)

        self._central_widget = QWidget()
        self._central_widget.setLayout(layout)
        self.setCentralWidget(self._central_widget)

    def _create_menu(self):
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction("Quit", self.close, "Ctrl+Q")
        self.file_menu.addAction("Load Image", self._load_image_with_dialog, "Ctrl+I")
        self.file_menu.addAction("Load Configuration", self._load_config_with_dialog, "Ctrl+L")
        self.file_menu.addAction("New Configuration", self._new_configuration_dialog, "Ctrl+N")

    def _load_image_with_dialog(self):
        print("A File dialog box appears")
        ...

    def _load_config_with_dialog(self):
        print("A File dialog box appears")
        ...

    def _new_configuration_dialog(self):
        print("Would you like to save th current configuration file before closing ?")
        ...

    def _create_settings_panel(self):
        self._settings_panel = QGroupBox("Settings")
        layout = QVBoxLayout()
        for i in range(10):
            inline_layout = QHBoxLayout()
            inline_layout.addWidget(QLabel(f"setting {i + 1}:"))
            inline_layout.addWidget(QPushButton("button A"))
            inline_layout.addWidget(QPushButton("button B"))
            layout.addLayout(inline_layout)
        layout.addStretch()
        self._settings_panel.setLayout(layout)

    def _create_image_panel(self):
        default_image = QImage(str(files(spot_detector.resources).joinpath("testscreen.png")))
        pixmap = QPixmap.fromImage(default_image)
        label = QLabel("image")
        label.setPixmap(pixmap)
        self._image_panel = QScrollArea()
        self._image_panel.setWidgetResizable(True)
        self._image_panel.setMinimumSize(500, 500)
        self._image_panel.setWidget(label)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())


