from multiprocessing import Process, Queue, parent_process
from pathlib import Path
from time import sleep
from typing import Callable, cast
from datetime import datetime
from traceback import format_exc

import cv2 as cv
import numpy as np
from numpy import uint16

from spot_detector.custom_types import Bool2D, CommonInt_T, DataElement, ImageBGR, ShadeTable, ImageElement, ImageRGB
from spot_detector.errors import ImageError
from spot_detector.misc import canonical_path
from spot_detector.model.models import ColorAndParams, DetParams
from spot_detector.model.processing_settings_models import CroppingSettings, DustFilterSettings, PreprocessingSettings
from spot_detector.model.result_datastructures import CheckID, CheckReport, CheckStatus, ImageResult, ImageTask, ROIData
from spot_detector.processing.image_info import load_image_for_processing
from spot_detector.processing.transformations import (
    compute_dish_ROI_mask,
    convert_mat_uint16,
    evenly_spaced_gray_palette,
    isolate_categories,
    label_img_fastest_uint16,
)

type InQueueType = Queue[ImageElement | str]
type OutQueueType = Queue[DataElement]

RICH_KEYPOINTS = cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS



def count_spots_fourth_method(
    image: ImageRGB[uint16],
    color_table: ShadeTable,
    det_params: list[DetParams],
    _debug: int = 0,
) -> list[int]:
    # Use set to create a collection with a single item per unique value
    labels = list(set([int(x) for x in color_table[:, 3] if int(x) > 0]))  # pyright: ignore[reportAny]

    labeled = label_img_fastest_uint16(image, color_table)
    values: list[int] = []

    for i, settings in enumerate(det_params):
        j = i + 1  # 0 is the bg
        if j not in labels:
            # skip unused labels
            values.append(0)
            continue
        detector = cv.SimpleBlobDetector.create(settings.load_params(len(color_table)))
        isolated_color = isolate_categories(color_table, [j])

        gs_palette = evenly_spaced_gray_palette(isolated_color)

        gs_img = gs_palette[labeled.flatten()]
        gs_img = gs_img.reshape(image.shape[:2]).astype(np.uint8)

        key_points = detector.detect(gs_img)
        values.append(len(key_points))

    return values



def expand_debug(string: str) -> str:
    debug_path = Path("/Users/louis/Desktop/etalonnage/debug/")
    return str(debug_path.joinpath(string))



def img_processer(
    in_queue: InQueueType,
    out_queue: OutQueueType,
    config: ColorAndParams,
) -> None:
    """
    The target function if the workers. The workers terminate when they
    recieve a "STOP" string.
    `in_queue`: `multiprocessing.Queue` from which the function fetches
    `ImageElement`s.
    `out_queue`: `multiprocessing.Queue` to which processed data are output
    `config`: An object containing the different configurations necessary
    for computation. Must be picklable.
    """
    color_table = np.array([shade.as_row() for shade in config.shades])
    parent = parent_process()

    if parent is None:
        return

    while parent.is_alive():
        if in_queue.empty():
            sleep(1)
            continue

        job: str | ImageElement = in_queue.get()
        if isinstance(job, str):
            if job == "STOP":
                break
            print(f"Unexpected message recieved: {job}")
            continue

        folder_row, depth_col, path = job
        image = cast(ImageRGB[CommonInt_T] | None, cv.imread(path, cv.IMREAD_COLOR_BGR | cv.IMREAD_ANYDEPTH))
        if image is None:
            print(f"Failed reading image at path {path} and got None instead")
            continue

        image_16 = convert_mat_uint16(image)

        values = count_spots_fourth_method(image_16, color_table, config.det_params, _debug=0)
        result: DataElement = (folder_row, depth_col, values)
        out_queue.put(result)



def init_workers(
    count: int,
    config: ColorAndParams,
    in_queue: InQueueType,
    out_queue: OutQueueType,
    proc_func: Callable[[InQueueType, OutQueueType, ColorAndParams], None] = img_processer,
) -> list[Process]:
    """
    Creates a list of multiprocessing process objects but does not call
    their start method.
    :param count: The number of processes to create
    :param project: The project, including configuration of the detector for each label
    :param in_queue: The queue from which the processes fetch their input data
    :param out_queue: The queue to which the processed data is output
    :return: The list of process objects
    """
    workers_list: list[Process] = []
    for _ in range(count):
        worker = Process(target=proc_func, args=(in_queue, out_queue, config))
        workers_list.append(worker)
    return workers_list

def filter_image_dust(
    image: ImageBGR[uint16],
    df_settings: DustFilterSettings,
) -> tuple[ImageBGR[uint16], CheckReport]:

    if not df_settings.enabled:
        report = CheckReport(CheckID.Dust_Filter, CheckStatus.Disabled, None, "")
        return image, report

    report_message: str = ""
    if df_settings.path is None:
        filter = None
        report_message = "Dust filter path was not provided"
    else:
        try:
            filter, _ = load_image_for_processing(df_settings.path)
        except ImageError as e:
            report_message = e.msg
            filter = None

    if filter is None:
        report = CheckReport(CheckID.Dust_Filter, CheckStatus.Fail, None, report_message)
        return image, report

    if filter.shape != image.shape:
        report_message = (
            "Image and filter shapes do not match: "
            + f"image.shape={image.shape} ; filter.shape={filter.shape}"
        )
        report = CheckReport(CheckID.Dust_Filter, CheckStatus.Fail, None, report_message)
        return image, report

    diff = image.astype(np.int32) - filter.astype(np.int32)
    filtered = np.clip(diff, 0, 65535).astype(np.uint16)

    return filtered, CheckReport(CheckID.Dust_Filter, CheckStatus.Success, None, "")



def compute_roi(
    image: ImageBGR[uint16],
    roi_settings: CroppingSettings
) -> tuple[Bool2D, float, float, float] | None:
    if not roi_settings.enabled:
        return None

    max_rad = roi_settings.max_radius_value if roi_settings.max_radius_enabled else -1
    min_rad = roi_settings.min_radius_value if roi_settings.min_radius_enabled else -1
    rad_range = (min_rad, max_rad)

    res = compute_dish_ROI_mask(image, rad_range)
    if res is None:
        return None
    else:
        mask, (x, y, r) = res
        return mask, x, y, r



def apply_roi(
    image: ImageBGR[uint16],
    roi_compute_result: tuple[Bool2D, float, float, float] | None,
    roi_settings: CroppingSettings,
) -> tuple[ImageBGR[uint16], ROIData, CheckReport]:

    if not roi_settings.enabled:
        data = ROIData(CheckStatus.Disabled, None, None, None)
        report = CheckReport(CheckID.ROI, CheckStatus.Disabled, None, "")
        return image, data, report

    if roi_compute_result is None:
        data = ROIData(CheckStatus.Fail, None, None, None)
        message = "Failed to compute image ROI with the current settings, falling back to full image"
        report = CheckReport(CheckID.ROI, CheckStatus.Fail, None, message)
        return image, data, report

    mask, x, y, r = roi_compute_result
    min_y, max_y = max(0, int(y - r) + 1), min(int(y + r), image.shape[0])
    min_x, max_x = max(0, int(x - r) + 1), min(int(x + r), image.shape[1])

    crop = image[min_y:max_y, min_x:max_x, :].copy()
    new_mask = mask[min_y:max_y, min_x:max_x]

    crop[~new_mask] = 0



    data = ROIData(CheckStatus.Success, x, y, r)
    report = CheckReport(CheckID.ROI, CheckStatus.Success, None, "")
    return crop, data, report



def save_cropped_image(image: ImageBGR[uint16], roi_settings: CroppingSettings, report: CheckReport, image_task: ImageTask) -> CheckReport:
    if not roi_settings.save_cropped_enabled:
        return report

    if roi_settings.save_path is None:
        # ideally, the config is checked before processing and this code path cannot be reached
        if report.check_message:
            report.check_message += " ; "
        report.check_message += "Save path for cropped images was not defined. No image was saved"
        return report

    if report.check_status != CheckStatus.Success:
        if report.check_message:
            report.check_message += " ; "
        report.check_message += "The image was not cropped but will be saved anyway"

    save_dir = canonical_path(roi_settings.save_path) / image_task.image_path.parent.name
    stem = image_task.image_path.stem
    extra = f"_{image_task.rank}"
    suffix = ".tiff"

    path = save_dir / (stem + extra + suffix)

    saved = False
    i = 2

    while not saved and i < 10:
        if not path.exists():
            saved = cv.imwrite(str(path), image)
        path = save_dir / (stem + extra + f"_{i}" + suffix)
        i += 1

    if not saved:
        if report.check_message:
            report.check_message += " ; "
        report.check_message += "Too many files exist with a similar name, aborting"

    return report



def process_image(
    task: ImageTask,
    detection_settings: ColorAndParams,
    preproc_settings: PreprocessingSettings,
) -> ImageResult:
    proc_date = datetime.now()

    error_cause: str | None = None
    error_detail: str = ""
    checks: dict[CheckID, CheckReport] = {}

    try:
        image, metadata = load_image_for_processing(task.image_path)
    except ImageError as e:
        error_detail += format_exc()
        error_cause = e.msg
        image, metadata = None, None

    if image is None:
        res = ImageResult( task, None,
            ROIData(CheckStatus.Fail, None, None, None),
            checks, proc_date, metadata, error_cause, error_detail)
        return res

    filtered, report = filter_image_dust(image, preproc_settings.dust_filter)
    checks[report.check_id] = report

    res = compute_roi(filtered, preproc_settings.cropping)
    # V V V checks requiring ROI and an uncropped image go here V V V

    cropped, roi_data, report = apply_roi(image, res, preproc_settings.cropping)
    report = save_cropped_image(cropped, preproc_settings.cropping, report, task)

    color_table = np.array([shade.as_row() for shade in detection_settings.shades])
    counts = count_spots_fourth_method(cropped, color_table, detection_settings.det_params)

    result = ImageResult(
        image_task=task,
        counts=counts,
        roi_data=roi_data,
        checks=checks,
        processing_date=proc_date,
        metadata=metadata,
        error=error_cause,
        error_detail=error_detail,
    )

    return result

