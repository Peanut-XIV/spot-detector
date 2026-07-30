import sys
from enum import IntEnum

from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QWidget,
    QApplication,
    QHBoxLayout,
)
from PySide6.QtCore import (
    QFile,
    QIODevice,
    QTextStream,
    Qt,
    Slot,
)

# //////// DO NOT REMOVE ////////
from spot_detector import rc_resources, rc_documentation  # noqa: F401 WARN: Do not remove

class Hint(IntEnum):
    DEFAULT = 0
    COLORS = 1
    MIN_DIST = 2
    THRESH = 3
    AREA = 4
    CIRC = 5
    INERTIA = 6
    CONV = 7
    MISSING = 8

    def as_file_name(self) -> str:
        match self:
            case Hint.DEFAULT:
                return "hint_default.html"
            # TODO : Add case Hint.COLORS
            # TODO : Add case Hint.MIN_DIST
            case Hint.AREA:
                return "hint_area.html"
            case Hint.CIRC:
                return "hint_circularity.html"
            case Hint.CONV:
                return "hint_convexity.html"
            case Hint.INERTIA:
                return "hint_inertia.html"
            case Hint.THRESH:
                return "hint_threshold.html"
            case Hint.MISSING:
                return "not_found.html"

            case other:
                print(f"Hint {other.__str__} not recognised")
                return "not_found.html"

    @staticmethod
    def hint_count() -> int:
        return 9


class HintPanel(QWidget):
    def __init__(
        self, parent: QWidget | None = None, scroll_area: QScrollArea | None = None
    ) -> None:
        super().__init__(parent)
        self.scroll_area: QScrollArea | None = scroll_area
        layout = QHBoxLayout(self)
        doc_path = ":resources/docs/"
        # TODO: Add the remaining docs please

        self.pages: dict[Hint, HintPage] = {}

        for hint_idx in range(Hint.hint_count()):
            hint = Hint(hint_idx)
            page = HintPage(hint, doc_path + hint.as_file_name(), self)
            page.setVisible(False)
            layout.addWidget(page)
            self.pages[hint] = page
        self.setLayout(layout)
        self.pages[Hint.DEFAULT].setVisible(True)
        self.current_page_id: Hint = Hint.DEFAULT

    @property
    def current_page(self):
        return self.pages[self.current_page_id]

    @Slot(Hint)
    def select_hint(self, id: Hint):
        id = id if id in self.pages else Hint.MISSING
        self.current_page.setVisible(False)
        self.current_page_id = id
        self.pages[id].setVisible(True)
        if self.scroll_area is not None:
            self.scroll_area.ensureVisible(0, 0)


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
        # TODO: Handle this case properly
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
