import sys
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QDialog,
    QSpinBox,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
)
from PySide6.QtCore import (
    Slot,
    Qt,
    QObject,
    QThread,
    Signal,
)
from numpy.typing import NDArray
from spot_detector.transformations import get_k_means
from spot_detector.model.reference_image import to_3_channel_mat, to_uint16_mat


class KMeansDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Dialog,
    ) -> None:
        super().__init__(parent, f)

        layout = QVBoxLayout(self)
        prompt = QLabel(
            "Select the number of labels used to quantize the reference image:", self
        )
        layout.addWidget(prompt)
        line1 = self.create_line1()
        layout.addLayout(line1)
        line2 = self.create_line2()
        layout.addLayout(line2)
        self.value = self.count_spinbox.value()

    def create_line1(self):
        line1 = QHBoxLayout()
        line1.addWidget(QLabel("Number of labels:", self))
        spinbox = QSpinBox(self)
        spinbox.setMinimum(2)
        spinbox.setMaximum(50)
        spinbox.setValue(10)
        self.count_spinbox = spinbox
        self.count_spinbox.valueChanged.connect(self.set_value)
        line1.addWidget(self.count_spinbox)
        return line1

    def create_line2(self):
        line2 = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setDefault(False)
        line2.addWidget(self.cancel_button)
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.accept)
        self.start_button.setDefault(True)
        line2.addWidget(self.start_button)
        return line2

    @Slot()
    def set_value(self, val: int):
        self.value = val

    def get_value(self):
        return self.value


class KmeansProcessor(QThread):
    result_ready = Signal(object)

    def __init__(self, image: NDArray, k: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Kmeans Processor Thread")
        self.k = k
        self.image = image

    def run(self) -> None:
        cast = to_uint16_mat(to_3_channel_mat(self.image))
        result = get_k_means(cast, self.k, 1e-4, 1000)
        self.result_ready.emit(result)


if __name__ == "__main__":

    class test_window(QMainWindow):
        def __init__(
            self,
            parent: QWidget | None = None,
            flags: Qt.WindowType = Qt.WindowType.Window,
        ) -> None:
            super().__init__(parent, flags)
            self.button = QPushButton("GO", self)
            self.button.clicked.connect(self.go)
            self.setCentralWidget(self.button)

        def go(self):
            dialog = KMeansDialog()
            dialog.exec()

    app = QApplication(sys.argv)
    win = test_window()
    win.show()
    sys.exit(app.exec())
