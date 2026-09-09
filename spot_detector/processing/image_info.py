# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2 as cv
import numpy as np
from numpy import uint16
from PIL import Image, UnidentifiedImageError
from PIL.JpegImagePlugin import get_sampling

from spot_detector.custom_types import ImageBGR
from spot_detector.errors import FailedOpeningError, InvalidFormatError, InvalidNameError
from spot_detector.model.result_datastructures import ImageMetaData
from spot_detector.processing.transformations import convert_mat_uint16

_LOSSY_FORMATS = frozenset({"JPEG", "JPEG2000", "MPO", "WEBP"})
_LOSSY_COMPRESSIONS = frozenset({"jpeg", "webp"})
_JPEG_SAMPLING = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}

_EXIF_MODEL = 272
_EXIF_DATETIME = 306
_EXIF_EXPOSURE_TIME = 33434


@dataclass(frozen=True)
class _HeaderInfo:
    image_format: str
    image_codec: str
    has_lossy_compression: bool
    color_space: str
    subsampling: str
    creation_date: datetime | None
    camera_model: str
    exposure_seconds: float


def _read_header(descriptor: Image.Image) -> _HeaderInfo:
    """Read what the container declares, without decoding any pixel."""
    image_format = descriptor.format or ""
    codec = str(descriptor.info.get("compression", "") or image_format.lower())

    subsampling = ""
    if image_format.upper() == "JPEG":
        subsampling = _JPEG_SAMPLING.get(get_sampling(descriptor), "unknown")

    try:
        exif = descriptor.getexif()
    except Exception:
        exif = {}

    creation_date: datetime | None = None
    stamp = exif.get(_EXIF_DATETIME)
    if isinstance(stamp, str):
        try:
            creation_date = datetime.strptime(stamp.strip(), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            creation_date = None

    exposure = exif.get(_EXIF_EXPOSURE_TIME)
    try:
        exposure_seconds = float(exposure) if exposure is not None else 0.0  # pyright: ignore[reportUnknownArgumentType]
    except (TypeError, ValueError, ZeroDivisionError):
        exposure_seconds = 0.0

    model = exif.get(_EXIF_MODEL)

    return _HeaderInfo(
        image_format=image_format,
        image_codec=codec,
        has_lossy_compression=(
            image_format.upper() in _LOSSY_FORMATS or codec.lower() in _LOSSY_COMPRESSIONS
        ),
        color_space=descriptor.mode,
        subsampling=subsampling,
        creation_date=creation_date,
        camera_model=model.strip() if isinstance(model, str) else "",
        exposure_seconds=exposure_seconds,
    )


def load_image_for_processing(image_path: str | Path) -> tuple[ImageBGR[uint16], ImageMetaData]:
    """Open an image, guarantee its shape and datatype, and describe it.

    Pillow reads the header, which costs nothing since no pixel is decoded;
    OpenCV decodes, as the rest of the chain expects its BGR ordering and its
    handling of 48 bit TIFF files. Every failure raises: the caller turns the
    exception into a failed `ImageResult`, it is never swallowed here.
    """
    path = Path(image_path)

    if path.name.startswith("."):
        raise InvalidNameError(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_dir():
        raise IsADirectoryError(path)
    if not path.is_file():
        raise FailedOpeningError(path, "The path does not designate a regular file")

    try:
        with Image.open(path) as descriptor:
            header = _read_header(descriptor)
    except UnidentifiedImageError as error:
        raise FailedOpeningError(path, "The file is not a recognised image") from error
    except OSError as error:
        raise FailedOpeningError(path, f"The image header could not be read: {error}") from error

    raw: ImageBGR[Any] | None = cv.imread(str(path), cv.IMREAD_COLOR_BGR | cv.IMREAD_ANYDEPTH)  # pyright: ignore[reportExplicitAny]
    if raw is None:
        raise FailedOpeningError(path, "The image could not be decoded")

    if raw.ndim != 3 or raw.shape[2] != 3:
        raise InvalidFormatError(path, f"Expected three colour channels, got shape {raw.shape}")
    if not np.issubdtype(raw.dtype, np.integer):
        raise InvalidFormatError(path, f"Expected an integer datatype, got {raw.dtype}")

    try:
        image: ImageBGR[uint16] = convert_mat_uint16(raw)
    except TypeError as error:
        raise InvalidFormatError(path, f"Unsupported datatype {raw.dtype}") from error

    metadata = ImageMetaData(
        creation_date=header.creation_date or datetime.fromtimestamp(path.stat().st_mtime),
        image_format=header.image_format,
        image_codec=header.image_codec,
        has_lossy_compression=header.has_lossy_compression,
        color_space=header.color_space,
        subsampling=header.subsampling,
        image_height=int(raw.shape[0]),
        image_width=int(raw.shape[1]),
        channel_depth=int(raw.dtype.itemsize * 8),
        camera_model=header.camera_model,
        exposure_seconds=header.exposure_seconds,
    )
    return image, metadata
