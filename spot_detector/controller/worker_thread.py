from pathlib import Path

import numpy as np
from numpy import uint16
from numpy.typing import NDArray
from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
)

from spot_detector.custom_types import ImageRGB, ShadeTable
from spot_detector.model.models import Shade
from spot_detector.processing.image_validation.blur_calibration import (
    BlurCalibration,
    calibrate_blur,
)
from spot_detector.processing.image_validation.image_context import ImageContext
from spot_detector.processing.transformations import (
    convert_mat_uint16,
    label_img_fastest_uint16,
)


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



class BlurCalibrationProcessor(QThread):
    """Calibration du seuil de flou sur une serie d'images de reference.

    Le calcul est deporte parce qu'il est lourd : une labellisation par image,
    plus une par copie floutee, chacune materialisant un tableau de H*W*N*3
    flottants. Le lancer sur le fil d'interface figerait la fenetre pendant
    tout le calcul.
    """

    result_ready: Signal = Signal(object)   # BlurCalibration
    failed: Signal = Signal(str)

    def __init__(
        self,
        reference_paths: list[Path],
        shades: ShadeTable,
        reject_sigma: float,
        candidate_diameters_px: tuple[int, ...] | None = None,
        collar_fraction: float = 0.5,
        min_particles: int = 30,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("Blur Calibration Processor Thread")
        self.reference_paths: list[Path] = reference_paths
        self.shades: ShadeTable = shades
        self.reject_sigma: float = reject_sigma
        self.candidate_diameters_px: tuple[int, ...] | None = candidate_diameters_px
        self.collar_fraction: float = collar_fraction
        self.min_particles: int = min_particles

    def run(self):
        images: list[ImageRGB[uint16]] = []
        unreadable: list[Path] = []

        for path in self.reference_paths:
            image = ImageContext(path, self.shades).image
            if image is None:
                unreadable.append(path)
            else:
                images.append(image)

        if not images:
            self.failed.emit(
                "None of the selected reference images could be read."
            )
            return

        extra_arguments = {}
        if self.candidate_diameters_px is not None:
            extra_arguments["candidate_diameters_px"] = self.candidate_diameters_px

        try:
            calibration: BlurCalibration = calibrate_blur(
                images,
                self.shades,
                collar_fraction=self.collar_fraction,
                reject_sigma=self.reject_sigma,
                min_particles=self.min_particles,
                **extra_arguments,
            )
        except ValueError as error:
            self.failed.emit(str(error))
            return

        for path in unreadable:
            calibration.warnings.append(f"Skipped unreadable file: {path}")

        self.result_ready.emit(calibration)
