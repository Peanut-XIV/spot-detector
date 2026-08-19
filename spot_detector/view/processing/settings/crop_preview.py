from pathlib import Path
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from numpy import uint8
from numpy.typing import NDArray

from spot_detector.view.dialogs.custom_dialog_base import CustomModalDialog

from spot_detector import rc_resources  # pyright: ignore[reportUnusedImport]  # noqa: F401


class ImageListPreview(CustomModalDialog):
    def __init__(
        self,
        image_list: list[tuple[Path, NDArray[uint8] | None]] | None = None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window
    ) -> None:
        super().__init__(parent, f)

        self.index: int = 0
        self.image_list: list[tuple[Path, NDArray[uint8] | None]] = image_list or []

        self._init_layout()

        _ = self.first_button.clicked.connect(self.go_first)
        _ = self.prev_button.clicked.connect(self.go_previous)
        _ = self.next_button.clicked.connect(self.go_next)
        _ = self.last_button.clicked.connect(self.go_last)
        _ = self.accept_button.clicked.connect(self.accept)

        self.update_layout()

    def _init_layout(self):
        layout = QVBoxLayout(self)

        self.image_path_label: QLabel = QLabel("[No Image to Display!]", self, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_path_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.image_view: QLabel = QLabel(self)
        self.image_view.setBackgroundRole(QPalette.ColorRole.Dark)
        layout.addWidget(self.image_view, alignment=Qt.AlignmentFlag.AlignCenter)

        button_layout = QHBoxLayout()
        self.first_button: QPushButton = QPushButton("First", self)
        self.prev_button:  QPushButton = QPushButton("Previous", self)
        self.list_status:  QLabel = QLabel("-/-", alignment=Qt.AlignmentFlag.AlignCenter)
        self.next_button:  QPushButton = QPushButton("Next", self)
        self.last_button:  QPushButton = QPushButton("Last", self)

        button_layout.addWidget(self.first_button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.prev_button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        button_layout.addWidget(self.list_status, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        button_layout.addWidget(self.next_button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.last_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(button_layout)

        self.accept_button: QPushButton = QPushButton("Ok", self)
        layout.addWidget(self.accept_button)

    @property
    def count(self):
        return len(self.image_list)

    def update_layout(self):
        count = self.count
        new_text = f"image {self.index + 1}/{count}" if count > 0 else "-/-"
        self.list_status.setText(new_text)

        im_path, im_mat = self.image_list[self.index] if (0 <= self.index < count) else (None, None)

        path_text = "[No Path To Display!]" if im_path is None else f"Original File: {str(im_path)}"
        self.image_path_label.setText(path_text)

        if im_mat is None:
            image = QImage(":resources/images/testscreen.png")
        else:
            shape = im_mat.shape
            h = int(shape[0])  # pyright: ignore[reportAny]
            w = int(shape[1])  # pyright: ignore[reportAny]

            image = QImage(im_mat.data, int(w), int(h), int(w*3), QImage.Format.Format_BGR888)

        image_tf = image.scaledToWidth(300)

        self.image_view.setPixmap(QPixmap(image_tf))

    def go_first(self):
        self.index = 0
        self.update_layout()

    def go_last(self):
        count = len(self.image_list)
        self.index = count - 1 if count <= 0 else 0
        self.update_layout()

    def go_previous(self):
        next_index = self.index - 1
        count = len(self.image_list)
        self.index = next_index if 0 <= next_index < count else 0
        self.update_layout()

    def go_next(self):
        next_index = self.index + 1
        count = len(self.image_list)
        self.index = next_index if 0 <= next_index < count else max(count - 1, 0)
        self.update_layout()


def mat_to_QImage(mat: NDArray[uint8]) -> QImage:
    image = QImage(
        mat.data,
        mat.shape[1],  # pyright: ignore[reportAny]
        mat.shape[0],  # pyright: ignore[reportAny]
        QImage.Format.Format_BGR888,
    )

    return image


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = ImageListPreview()
    widget.show()
    sys.exit(app.exec())
