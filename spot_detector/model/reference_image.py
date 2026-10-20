from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, PrivateAttr
from PySide6.QtGui import QImage

from spot_detector.custom_types import Array2D, ImageBGR, NVec, PixTuple, ShadeTuple
from spot_detector.errors import (
    FailedOpeningError,
    InvalidFormatError,
    InvalidNameError,
)
from spot_detector.misc import canonical_path
from spot_detector.model.models import Shade
from spot_detector.processing.transformations import (
    get_k_means,
)


def to_displayable_mat(mat: NDArray[np.generic]) -> ImageBGR[np.uint8]:
    return np.ascontiguousarray(to_3_channel_mat(to_uint8_mat(mat)))


def to_3_channel_mat[T: np.generic](mat: NDArray[T]) -> ImageBGR[T]:
    match mat.ndim:
        case 2:
            return mat.repeat(3, 2)
        case 3:
            shape = mat.shape
            match cast(tuple[int, int, int], shape):
                case x, y, _ if x == 1 or y == 1:
                    pass
                case _, _, 1:
                    return mat.repeat(3, 2)
                case x, y, 2:
                    zeros = np.zeros([x, y], mat.dtype)
                    return np.stack([mat, zeros], 2)
                case _, _, 3:
                    return mat
                case _, _, 4:
                    return mat[:, :, 0:3]
                case _:
                    pass
        case _:
            pass
    raise ValueError(
        f"Unexpected ndarray shape {mat.shape}. Expected one of the "
        + "following: [x, y], [x, y, 1], [x, y, 2], [x, y, 3], [x, y, 4]"
        + " where x and y are both greater than 1"
    )


def to_uint8_mat(mat: NDArray[np.generic]) -> NDArray[np.uint8]:
    dtype = mat.dtype
    if np.isdtype(dtype, np.uint8):
            mat = cast(NDArray[np.uint8], mat)
            return mat.copy()
    if np.isdtype(dtype, np.uint16):
            mat = cast(NDArray[np.uint16], mat)
            return (mat >> 8).astype(np.uint8)
    if np.isdtype(dtype, np.uint32):
            mat = cast(NDArray[np.uint32], mat)
            return (mat >> 24).astype(np.uint8)
    if np.isdtype(dtype, np.uint64):
            mat = cast(NDArray[np.uint64], mat)
            return (mat >> 56).astype(np.uint8)
    if np.isdtype(dtype, (np.float32, np.float64)):
            mat = cast(NDArray[np.float32], mat)
            new_mat = np.clip(mat * 256, 0.0, 255.0).astype(np.uint8)
            return new_mat
    raise TypeError(
        f"Got image matrix with datatype {dtype} but expected one of the "
        + "following : uint8, uint16, uint32, uint64, float32, float64"
    )


def to_uint16_mat(mat: NDArray[np.generic]) -> NDArray[np.uint16]:
    dtype = mat.dtype
    if np.isdtype(dtype, np.uint8):
            mat = cast(NDArray[np.uint8], mat)
            return np.left_shift(mat, 8, dtype=np.uint16)
    if np.isdtype(dtype, np.uint16):
            mat = cast(NDArray[np.uint16], mat)
            return mat.copy()
    if np.isdtype(dtype, np.uint32):
            mat = cast(NDArray[np.uint32], mat)
            return (mat >> 16).astype(np.uint16)
    if np.isdtype(dtype, np.uint64):
            mat = cast(NDArray[np.uint64], mat)
            return (mat >> 48).astype(np.uint16)
    if np.isdtype(dtype, (np.float32, np.float64)):
            mat = cast(NDArray[np.float32], mat)
            new_mat = np.clip(mat * 65536, 0.0, 65535.0).astype(np.uint16)
            return new_mat
    raise TypeError(
        f"Got image matrix with datatype {dtype} but expected one of the "
        + "following : uint8, uint16, uint32, uint64, float32, float64"
    )


def validate_mat(mat: NDArray[np.generic]) -> None:
    if not mat.ndim == 3 and mat.shape[2] == 3:
        raise ValueError(
            f"Got image matrix of shape {mat.shape} but expected shape "
            + "[x, y, 3]"
        )

    match mat.dtype:
        case np.uint8 | np.uint16 | np.uint32 | np.float32 | np.float64:
            pass
        case other_type:
            raise TypeError(
                f"Got image matrix with datatype {other_type} but expected"
                + " one of the following : uint8, uint16, uint32, float32, "
                + "float64"
            )


class ImageCache:
    def __init__(self, mat: ImageBGR[np.generic]) -> None:
        self.raw_mat: ImageBGR[np.generic]
        self.displayable_mat: ImageBGR[np.uint8]
        self.image: QImage

        self.set_mat(mat)

    def set_mat(self, mat: ImageBGR[np.generic]) -> None:
        self.raw_mat = mat
        self.displayable_mat = np.ascontiguousarray(to_displayable_mat(mat))
        self.image = QImage(
            self.displayable_mat.data,
            self.displayable_mat.shape[1],
            self.displayable_mat.shape[0],
            self.displayable_mat.strides[0],
            QImage.Format.Format_BGR888,
        )


# TODO: Add a method for generating all the matrices from a palette
class ReferenceImageMatrices:
    """
    A class for caching computations made on the reference image
    """

    def __init__(self, mat: NDArray[np.generic]) -> None:
        validate_mat(mat)
        self.reference: ImageCache = ImageCache(mat)

        # TODO: the rest is dependent on wether self.labeled_mat is defined
        #       or None.
        #     > If labeled mat exists, the rest can be generated maybe they
        #       should belong to another object that could be initialized or
        #       not.

        self.palettized: ImageCache | None = None
        self.highlight: ImageCache | None = None

        self.labels: Array2D[np.integer] | None = None

    def palettize_reference_from_kmeans(self, shade_count: int):
        """
        UNUSED - NEEDS TO BE THREADED

        Applies K-means to raw reference mat, converted to uint16
        creates or updates. It is important to update the colortable
        with the new colortable.
        """
        palettizable = to_3_channel_mat(to_uint16_mat(self.reference.raw_mat))
        lut, palettized, labels = get_k_means(palettizable, shade_count)
        self.update_palettized_and_labels(palettized, labels)
        return lut

    def update_labels(
        self,
        labels: Array2D[np.integer],
        label_shades: list[Shade],
        do_update_highlight: bool = True,
    ) -> None:
        """
        Creates a palettized ref image from an existing color table.
        Could be used to generate the image cache from an existing project
        file.
        """
        table = [shade.as_row() for shade in label_shades]
        lut = np.array(table)[:, 0:3].astype(np.uint16)
        self.labels = labels

        palettized = lut[labels]
        self.update_palettized(palettized)
        if do_update_highlight:
            self.update_highlight(palettized)

    def update_palettized_and_labels(self, palettized: ImageBGR[np.generic], labels: NVec[np.integer]):
        im_shape = (palettized.shape[0], palettized.shape[1])
        self.update_palettized(palettized)
        self.update_highlight(palettized)
        self.labels = labels.reshape(im_shape)

    def apply_color_list(
        self, colors: list[ShadeTuple] | list[PixTuple]
    ) -> NDArray[np.uint16]:
        """
        can raise a ValueError if labeled_mat is not initialized yet
        """
        if self.labels is not None:
            lut = np.array(colors).astype(np.uint16)[:, 0:3]
            return lut[self.labels]
        else:
            raise ValueError(
                "'labeled_mat' must be non null. Palettize the reference image"
                + " first to be able to apply a palette."
            )

    def highlight_selection(self, selection: list[bool], shades: list[Shade]) -> None:
        color_list: list[PixTuple] = []
        for sel, shade in zip(selection, shades):
            if sel:
                # color tables coded in 16 bits channel depth
                color_list.append((65535, 65535, 0))
            else:
                color_list.append(shade.as_row()[0:3])

        highlight = self.apply_color_list(color_list)
        self.update_highlight(highlight)

    def update_highlight(self, mat: NDArray[np.generic]):
        if self.highlight is None:
            self.highlight = ImageCache(mat)
        else:
            self.highlight.set_mat(mat)

    def update_palettized(self, mat: NDArray[np.generic]):
        if self.palettized is None:
            self.palettized = ImageCache(mat)
        else:
            self.palettized.set_mat(mat)


class ReferenceImageModel(BaseModel):
    path: str = Field()
    _cache: ReferenceImageMatrices = PrivateAttr()

    def __init__(self, /, init_cache: bool = True, **data: Any) -> None:  # pyright: ignore[reportExplicitAny, reportAny]
        super().__init__(**data)
        if init_cache:
            self.generate_cache_from_path()

    @property
    def mats(self):
        return self._cache

    def generate_cache_from_mat(self, mat: NDArray[np.generic]):
        try:
            self._cache = ReferenceImageMatrices(mat)
        except (ValueError, TypeError) as e:
            error = InvalidFormatError(
                self.path,
                f"Error caused by: {e}",
            )
            raise error

    # TODO: Merge with Main_window.validate_reference_image()
    def generate_cache_from_path(self):
        true_path = canonical_path(self.path)
        if Path(true_path).name.startswith("."):
            raise InvalidNameError(true_path)
        img = cv2.imread(true_path, cv2.IMREAD_COLOR_BGR | cv2.IMREAD_ANYDEPTH)
        if img is None:
            raise FailedOpeningError(true_path)
        self.generate_cache_from_mat(img)

    def without_cache(self) -> "ReferenceImageModel":
        """Return the same model with no image cache attached.

        The cache holds `QImage` objects, which can neither be deep copied nor
        pickled, so any copy of a project meant to be serialised or sent to
        another process has to leave it behind. The result carries the path,
        which is all a snapshot needs; reading `mats` on it raises, by design.
        """
        return ReferenceImageModel(path=self.path, init_cache=False)

    def set_path(self, path: str | Path):
        path = Path(path)
        self.path = str(path)
        self.generate_cache_from_path()
