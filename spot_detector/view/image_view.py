from typing import Optional
from PySide6.QtGui import (
    QImage,
)
from PySide6.QtWidgets import (
    QWidget,
    QScrollArea,
)


class ImagePanel(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        ...
    
    def update_image(self, image: QImage) -> None:
        ...

