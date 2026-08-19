from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, TypeAlias

import cv2 as cv
import numpy as np
from numpy import uint8
from numpy.typing import DTypeLike, NDArray

from spot_detector.file_utils import VALID_IMAGE_TYPES
from spot_detector.model.processing_settings_models import CroppingSettings
from spot_detector.processing.image_validation.image_context import ImageContext
from spot_detector.processing.transformations import convert_mat_uint8, crop_to_dish_roi
from spot_detector.view.processing.file_selection.file_selection_items import (
    FileStatus,
    QualityFlag,
    StatusUpdate,
)

# Un controle qualite lit un contexte deja constitue et rend un compte rendu.
# Le contexte porte la lecture du fichier et les derives couteux, de sorte que
# n controles sur un fichier ne coutent qu'une lecture et une labellisation.
CheckFn: TypeAlias = Callable[[ImageContext], StatusUpdate]


def check_file_access(context: ImageContext) -> StatusUpdate:
    file_path = context.path
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

    if context.raw is None:
        update.file_status = FileStatus.BadFormat
        update.error_messages.append(
            f"Error: file '{str(file_path)}' can be read but does not contain "
            + "a valid image. Please make sure the file is in one of the "
            + f"following formats : {VALID_IMAGE_TYPES} and that the file"
            + " extension was not modified."
        )

    return update


def file_error_in_quality_check(context: ImageContext) -> StatusUpdate:
    file_path = context.path
    status = check_file_access(context)

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
    context: ImageContext
) -> StatusUpdate:
    file_path = context.path
    update = StatusUpdate(file_path, None, None, [])
    flag_mask  = QualityFlag.Checked | QualityFlag.FilterFailsMatch
    flag_value = QualityFlag.Checked

    # Le tableau brut, pas context.image : ce dernier est toujours en uint16 et
    # masquerait une difference de profondeur avec le filtre.
    mat = context.raw

    if mat is None:
        return file_error_in_quality_check(context)

    if list(mat.shape) != list(shape) or mat.dtype != data_type:  # pyright: ignore[reportAny]
        flag_value |= QualityFlag.FilterFailsMatch
        update.error_messages.append(
            f"Warning: image located at '{str(file_path)}' has shape "
            + f"{mat.shape} and datatype {mat.dtype} but the dust "  # pyright: ignore[reportAny]
            + f"filter has shape {shape} and datatype {data_type}, "
            + "the filter cannot and will not be applied to this image"
        )

    update.quality_status = (flag_mask, flag_value)

    return update


def make_dust_filter_compat_checker(
    shape: list[int],
    data_type: DTypeLike
) -> CheckFn:

    def checker(context: ImageContext) -> StatusUpdate:
        return check_dust_filter_compat(shape, data_type, context)

    return checker

def make_autocropping_checker(
    config: CroppingSettings
) -> Callable[[ImageContext], tuple[NDArray[uint8] | None, StatusUpdate]]:
    def checker(context: ImageContext) -> tuple[NDArray[uint8] | None, StatusUpdate]:
        return check_autocropping(context, config)
    return checker


def check_autocropping(
    context: ImageContext,
    config: CroppingSettings
) -> tuple[NDArray[uint8] | None, StatusUpdate]:
    image_path = context.path
    image = context.raw

    if image is None:
        return (None, file_error_in_quality_check(context))

    image_mat = convert_mat_uint8(image)

    mini = config.min_radius_value if config.min_radius_enabled else -1
    maxi = config.max_radius_value if config.max_radius_enabled else -1

    print(f"before: {image_mat.shape}:{image_mat.dtype}")  # pyright: ignore[reportAny]

    cropped_image = crop_to_dish_roi(image_mat, (mini, maxi)).astype(np.uint8)

    print(f"after: {cropped_image.shape}:{cropped_image.dtype}")

    status = StatusUpdate(Path(image_path), FileStatus.Ok,
        (QualityFlag.Checked | QualityFlag.RoiFail, QualityFlag.Checked), [],)

    return cropped_image, status

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

def weird_tee(func: Callable[[T],tuple[U,V]]) -> Callable[[T], tuple[tuple[T,U],V]]:
    def teed_func(t: T) -> tuple[tuple[T,U],V]:
        u, v = func(t)
        return ((t,u),v)
    return teed_func

def check_blur(context: ImageContext, blur_threshold: float) -> StatusUpdate:
    image_path = context.path
    image = context.image
    if image is None:
        return file_error_in_quality_check(context)
    grayscale = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    laplacian = cv.Laplacian(grayscale, cv.CV_64F)
    variance = np.var(laplacian)  # pyright: ignore[reportAny]
    return StatusUpdate(image_path, FileStatus.Ok, (QualityFlag.Checked | QualityFlag.Blurry, QualityFlag.Checked), [])

