from typing import Self
from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QWidget,
        QVBoxLayout,
)
from PySide6.QtCore import Qt

class InstructionWidget(QWidget):
    def __init__(self, title: str, body: str, parent: QWidget | None = None, f: Qt.WindowType = Qt.WindowType.Widget) -> None:
        super().__init__(parent, f)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(title, self))
        text_block = QLabel(body, self)
        text_block.setWordWrap(True)
        layout.addWidget(text_block)
        layout.addStretch(1)
        self.setMinimumHeight(200)
        self.setVisible(False)
        self.setLayout(layout)


    @classmethod
    def as_default(cls, parent: QWidget | None = None) -> Self:
        title = "No field selected yet:"
        body = "Select a field in the configuration tree to display informations about it."
        return cls(title, body, parent)

    @classmethod
    def as_minimum_distance(cls, parent: QWidget | None = None) -> Self:
        title = "Minimum distance:"
        body = "This parameter sets the minimum valid distance between two blobs."
        return cls(title, body, parent)

    @classmethod
    def as_filter_by_area(cls, parent: QWidget | None = None) -> Self:
        title = "Filter by area:"
        body = "This parameter sets the minimum and maximum area of a blob in pixels. "\
               "The bounds are floating point numbers and must be positive."
        return cls(title, body, parent)

    @classmethod
    def as_filter_by_circularity(cls, parent: QWidget | None = None) -> Self:
        title = "Filter by circularity:"
        body = "This parameter allows to select objects from their similarity to circles. "\
               "The bounds are floating point numbers and must be between 0 and 1. The circularity "\
               "value is computed as circularity = (4×π×Area) / (Perimeter²)."
        return cls(title, body, parent)

    @classmethod
    def as_filter_by_convexity(cls, parent: QWidget | None = None) -> Self:
        title = "Filter by convexity:"
        body = "This parameter allows to select objects with a certain convexity. "\
               "The bounds are floating point numbers and must be between 0 and 1. "\
               "convexity is computed as the ratio between the shape's area and "\
               "it's convex hull."
        return cls(title, body, parent)

if __name__ == "__main__":
    app = QApplication()
    widget = QWidget()
    layout = QHBoxLayout()
    layout.addWidget(InstructionWidget.as_minimum_distance(widget))
    layout.addWidget(InstructionWidget.as_filter_by_area(widget))
    layout.addWidget(InstructionWidget.as_filter_by_circularity(widget))
    layout.addStretch(1)
    widget.setLayout(layout)
    widget.show()
    app.exec()
