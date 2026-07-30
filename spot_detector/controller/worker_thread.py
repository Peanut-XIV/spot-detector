from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
)
import numpy as np
from numpy.typing import NDArray

from spot_detector.model.models import Shade
from spot_detector.processing.transformations import convert_mat_uint16, label_img_fastest_uint16


class ReloadPaletteProcessor(QThread):
    result_ready: Signal = Signal(object)

    def __init__(
        self,
        image: NDArray,
        shades: list[Shade],
        parent: QObject | None = None
    ) -> None:
        super().__init__(parent)

        self.setObjectName("Reload Palette Processor Thread")
        self.image = image
        self.shades = shades

    def run(self):
        as_u16 = convert_mat_uint16(self.image)
        palette = np.array([list(shade.as_row()) for shade in self.shades])
        result = label_img_fastest_uint16(as_u16, palette)

        self.result_ready.emit(result)

