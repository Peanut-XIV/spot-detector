import sys
from importlib.resources import files
from typing import Self
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
        QLabel,
        QWidget,
        QApplication,
        QHBoxLayout,
        QVBoxLayout,
        QScrollArea,
)
from PySide6.QtCore import (
        QFile,
        QIODevice,
        QTextStream,
        Qt,
)
import spot_detector.rc_resources
from spot_detector.view.detection_settings import Hint


class HintPanel(QScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.selected_panel: Hint = Hint.DEFAULT
        layout = QHBoxLayout(self)
        page = HintPage.as_default(self)
        #page.setMaximumWidth(1000)
        layout.addWidget(page)
        self.setLayout(layout)

class HintPage(QWidget):
    def __init__(
            self,
            hint_id: Hint,
            parent: QWidget | None = None,
            f: Qt.WindowType = Qt.WindowType.Widget
    ) -> None:
        super().__init__(parent, f)
        self.id: Hint = hint_id

    @classmethod
    def as_default(
            cls, 
            parent: QWidget | None = None,
            f: Qt.WindowType = Qt.WindowType.Widget
    ) -> Self:
        page = cls(Hint.DEFAULT, parent, f)
        layout = QVBoxLayout(page)
        document = QLabel(page)

        text = print_file(":resources/docs/hint_default.html")

        document.setText(text)
        document.setWordWrap(True)
        layout.addWidget(document)
        page.setLayout(layout)
        return page


def print_file(file_path: str) -> str:
    file = QFile(file_path)
    text: str = ""
    flags = QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text
    if not file.open(flags):
        print("Could not open file", file_path)
    else:
        stream = QTextStream(file)
        while not stream.atEnd():
            text += stream.readLine()
    file.close()
    return text


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = HintPanel()
    panel.show()
    sys.exit(app.exec())
