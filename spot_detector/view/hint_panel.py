"""
I hope this file is useful...
"""

import sys
from PySide6.QtWidgets import (
    QLabel,
    QWidget,
    QApplication,
    QHBoxLayout,
    QScrollArea,
)
from PySide6.QtCore import (
    QFile,
    QIODevice,
    QTextStream,
    Qt,
    Slot,
)

# //////// DO NOT REMOVE ////////
import spot_detector.rc_resources

from spot_detector.types import Hint


class HintPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        doc_path = ":resources/docs/"
        # TODO: Add the remaining docs please
        docs_n_ids = [
            ["hint_default.html", Hint.MISSING],  # Make an ERROR PAGE NOT FOUND page
            ["hint_default.html", Hint.DEFAULT],
            ["hint_threshold.html", Hint.THRESH],
            ["hint_area.html", Hint.AREA],
            ["hint_circularity.html", Hint.CIRC],
            ["hint_convexity.html", Hint.CONV],
        ]
        self.pages: dict[Hint, HintPage] = {}
        for doc, id in docs_n_ids:
            page = HintPage(id, doc_path + doc, self)
            page.setVisible(False)
            layout.addWidget(page)
            self.pages[id] = page
        self.setLayout(layout)
        self.pages[Hint.DEFAULT].setVisible(True)
        self.current_page_id: Hint = Hint.DEFAULT

    @property
    def current_page(self):
        return self.pages[self.current_page_id]

    @Slot(Hint)
    def select_hint(self, id: Hint):
        print("recieved ID", id)
        next_page = self.pages.get(id, None)
        if next_page is None:
            print("Eh, this one does not exist (yet ?)")
            id = Hint.MISSING
            return
        self.current_page.setVisible(False)
        self.current_page_id = id
        self.pages[id].setVisible(True)


class HintPage(QLabel):
    def __init__(
        self,
        hint_id: Hint,
        document: str,
        parent: QWidget | None = None,
    ) -> None:
        text = print_file(document)
        super().__init__(text, parent)
        self.id: Hint = hint_id
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignTop)


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
