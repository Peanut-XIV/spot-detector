import sys
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QFrame
)
from PySide6.QtCore import Qt, Signal, Slot

class FileSelectionWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self._init_layout()

    def _init_layout(self):
        self._layout = QVBoxLayout(self)

        self._list_view = QTreeView(self)
        self._layout.addWidget(self._list_view)

        self._button_layout = QHBoxLayout()

        self._addfile_button = QPushButton("Add", self)
        self._button_layout.addWidget(self._addfile_button)

        self._removefile_button = QPushButton("Remove", self)
        self._button_layout.addWidget(self._removefile_button)

        self._button_layout.addStretch()

        self._filecount_label = QLabel("Total Files: 0", self)
        self._button_layout.addWidget(self._filecount_label)

        self._button_layout.addStretch()

        self._check_button = QPushButton("Check Files", self)
        self._button_layout.addWidget(self._check_button)

        self._layout.addLayout(self._button_layout)


class ErrorFeedbackBox(QWidget):

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self._init_layout()

    def _init_layout(self):
        self._layout = QVBoxLayout(self)

        self._top_line_layout = QHBoxLayout()

        self._error_count_label = QLabel("There is no error message currently", self)
        self._top_line_layout.addWidget(self._error_count_label)

        self._top_line_layout.addStretch()

        self._clear_button = QPushButton("Clear Messages", self)
        self._top_line_layout.addWidget(self._clear_button)

        self._layout.addLayout(self._top_line_layout)

        self._output_box = QLabel("")
        self._output_box.setFrameShape(QFrame.Shape.Panel)
        self._output_box.setFrameShadow(QFrame.Shadow.Sunken)
        self._output_box.setWordWrap(False)
        self._layout.addWidget(self._output_box)

    @Slot()
    def clear_messages(self):
        self._output_box.setText("")

    @Slot(str)
    def append_message(self, message: str):
        text = self._output_box.text()
        text += "\n" + message
        self._output_box.setText(text)



class FileSelectionPanel(QWidget):

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self._model = ...

        self._init_layout()

    def _init_layout(self):
        self._layout = QVBoxLayout(self)

        self._panel_title = QLabel("File Selection")
        self._layout.addWidget(self._panel_title)

        self._list_widget = FileSelectionWidget(self)
        self._layout.addWidget(self._list_widget)

        self._feedback_box = ErrorFeedbackBox(self)
        self._layout.addWidget(self._feedback_box)




if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = FileSelectionPanel()

    window.show()

    sys.exit(app.exec())
