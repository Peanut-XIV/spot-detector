"""Etat partage par les controles qualite portant sur un meme fichier.

Chaque controle avait sa propre lecture du fichier et sa propre labellisation.
La labellisation materialise un tableau de H*W*N*3 flottants, soit environ
4 Go sur une image 3712x5568 avec seize teintes : la refaire une fois par
controle est intenable des que plusieurs controles sont actifs.

Le contexte lit donc le fichier une fois, et calcule etiquettes, ROI et masque
de signal a la demande, en memorisant le resultat. Un controle qui n'a besoin
que de la forme du tableau ne declenche jamais la labellisation.
"""

from pathlib import Path

import cv2 as cv
import numpy as np
from numpy import uint8, uint16
from numpy.typing import NDArray

from spot_detector.processing.image_validation.blur_detection import (
    get_roi_mask,
    signal_mask_from_labels,
)
from spot_detector.processing.transformations import (
    convert_mat_uint16,
    label_img_fastest_uint16,
)
from spot_detector.types import Bool2D, CommonInt_T, ImageRGB, ShadeTable

# Les deux drapeaux vont toujours ensemble : COLOR_BGR garantit trois canaux
# meme pour un fichier gris, ANYDEPTH preserve les 16 bits par canal. L'un
# sans l'autre perd soit la profondeur, soit le nombre de canaux.
IMAGE_READ_FLAGS = cv.IMREAD_COLOR_BGR | cv.IMREAD_ANYDEPTH


class ImageContext:
    """Fichier image en cours de controle, et ses derives memorises.

    `shades` est la palette du projet, en ordre BGR comme `Shade.as_row`. Sans
    elle, `labels` et `signal_mask` restent None et les controles qui en
    dependent doivent se declarer non applicables.
    """

    def __init__(self, path: Path, shades: ShadeTable | None = None) -> None:
        self.path: Path = path
        self.shades: ShadeTable | None = shades

        self._read_attempted: bool = False
        self._raw: NDArray[CommonInt_T] | None = None
        self._image: ImageRGB[uint16] | None = None
        self._labels: NDArray[uint8] | None = None
        self._roi: Bool2D | None = None
        self._signal_mask: Bool2D | None = None

    def _read(self) -> None:
        if self._read_attempted:
            return
        self._read_attempted = True
        self._raw = cv.imread(str(self.path), IMAGE_READ_FLAGS)  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def raw(self) -> NDArray[CommonInt_T] | None:
        """Tableau tel que lu, sans conversion. C'est lui qu'il faut comparer a
        un filtre de reference : `image` est toujours en uint16 et masquerait
        une difference de profondeur."""
        self._read()
        return self._raw

    @property
    def image(self) -> ImageRGB[uint16] | None:
        """Image BGR 16 bits par canal. None si le fichier n'est pas lisible."""
        if self._image is None and self.raw is not None:
            self._image = convert_mat_uint16(self.raw)
        return self._image

    @property
    def roi(self) -> Bool2D | None:
        """Region utile. A defaut de ROI fournie, le plus grand cercle inscrit,
        qui ecarte le rebord de la boite de Petri."""
        if self._roi is None and self.image is not None:
            self._roi = get_roi_mask(self.image, None)
        return self._roi

    @property
    def labels(self) -> NDArray[uint8] | None:
        """Index de teinte par pixel. C'est le calcul couteux du contexte, et
        il n'a lieu qu'a la premiere demande."""
        if self._labels is None and self.image is not None and self.shades is not None:
            palette = np.ascontiguousarray(self.shades[:, :3])
            self._labels = label_img_fastest_uint16(self.image, palette)
        return self._labels

    @property
    def signal_mask(self) -> Bool2D | None:
        """Pixels de luminophores dans la ROI."""
        if self._signal_mask is None:
            labels, roi = self.labels, self.roi
            if labels is not None and roi is not None and self.shades is not None:
                self._signal_mask = signal_mask_from_labels(labels, self.shades, roi)
        return self._signal_mask
