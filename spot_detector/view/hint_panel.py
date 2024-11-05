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
        Qt,
)
import spot_detector.resources
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
        text: str = ""
        path = files(spot_detector.resources) / "docs" / "hint_default.html"
        with open(path) as html_file:
            for line in html_file.readlines():
                text += line
        document.setText(text)
        document.setWordWrap(True)
        layout.addWidget(document)
        page.setLayout(layout)
        return page


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = HintPanel()
    panel.show()
    sys.exit(app.exec())
