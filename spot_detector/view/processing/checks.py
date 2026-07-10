from pathlib import Path
from typing import Callable

import cv2 as cv
from numpy.typing import DTypeLike

from spot_detector.file_utils import VALID_IMAGE_TYPES
from spot_detector.view.file_selection.file_selection_items import (
    FileStatus,
    QualityFlag,
    StatusUpdate,
)


def check_file_access(file_path: Path) -> StatusUpdate:
    update = StatusUpdate(file_path, FileStatus.Ok, None, [])

    try:

        with open(file_path, "rb") as f:
            _: bytes = f.read(10)

    except FileNotFoundError:
        update.error_messages.append(f"Error: file '{str(file_path)}' could not be found")
        update.file_status = FileStatus.NotFound
        return update

    except PermissionError:
        update.error_messages.append(
            f"Error: file '{str(file_path)}' could not be opened "
            + "because the application does not have the permission"
        )
        update.file_status = FileStatus.NoAuth
        return update

    mat = cv.imread(str(file_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH)

    if mat is None:
        update.file_status = FileStatus.BadFormat
        update.error_messages.append(
            f"Error: file '{str(file_path)}' can be read but does not contain "
            + "a valid image. Please make sure the file is in one of the "
            + f"following formats : {VALID_IMAGE_TYPES} and that the file"
            + " extension was not modified."
        )

    return update


def file_error_in_quality_check(file_path: Path) -> StatusUpdate:
    status = check_file_access(file_path)

    assert status.file_status is not None

    if status.file_status in [FileStatus.BadFormat, FileStatus.NoAuth, FileStatus.NotFound]:
        return status

    new_file_status = FileStatus.BadFormat
    message = (
         f"File Error: file located at '{file_path}' has an incoherent behavior"
        + " when opened, please make sure it is not used by another application"
        + " at the same time and try again or use another one."
    )

    return StatusUpdate(file_path, new_file_status, None, [message])

def check_dust_filter_compat(
    shape: list[int],
    data_type: DTypeLike,
    file_path: Path
) -> StatusUpdate:
    update = StatusUpdate(file_path, None, None, [])
    flag_mask  = QualityFlag.Checked | QualityFlag.BadFilterShape
    flag_value = QualityFlag.Checked

    mat = cv.imread(str(file_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH)

    if mat is None:
        return file_error_in_quality_check(file_path)

    if list(mat.shape) != list(shape):  # pyright: ignore[reportAny]
        flag_value |= QualityFlag.BadFilterShape
        update.error_messages.append(
            f"Warning: image located at '{ str(file_path) }' has shape "
            + f"{ mat.shape } but the dust filter has shape { shape }, "  # pyright: ignore[reportAny]
            +  "the filter cannot and will not be applied to this image"
        )

    if mat.dtype != data_type:
        flag_value |= QualityFlag.BadFilterShape
        update.error_messages.append(
            "Warning: image located at '{str(file_path)}' has datatype "
            + f"{mat.dtype} but the dust filter has shape {data_type}, "
            + "the filter cannot and will not be applied to this image"
        )

    update.quality_status = (flag_mask, flag_value)

    return update


def make_dust_filter_compat_checker(
    shape: list[int],
    data_type: DTypeLike
) -> Callable[[Path], StatusUpdate]:

    def checker(file_path: Path) -> StatusUpdate:
        return check_dust_filter_compat(shape, data_type, file_path)

    return checker
