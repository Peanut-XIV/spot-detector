from multiprocessing import Process, Queue, parent_process
from pathlib import Path
from time import sleep
from typing import Callable, cast

import cv2 as cv
import numpy as np
from numpy import uint16
import random

from spot_detector.model.models import ColorAndParams, DetParams
from spot_detector.processing.transformations import (
    convert_mat_uint16,
    evenly_spaced_gray_palette,
    isolate_categories,
    # label_img_fastest,
    label_img_fastest_uint16,
)

from spot_detector.custom_types import CommonInt_T, DataElement, ShadeTable, ImageElement, ImageRGB
from spot_detector.processing.visualisation import visualize_detection

type InQueueType = Queue[ImageElement | str]
type OutQueueType = Queue[DataElement]

RICH_KEYPOINTS = cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS


def count_spots_fourth_method(
    image: ImageRGB[uint16],
    color_table: ShadeTable,
    det_params: list[DetParams],
    debug: int = 0,
) -> list[int]:
    # Use set to create a collection with a single item per unique value
    labels = list(set([int(x) for x in color_table[:, 3] if int(x) > 0]))  # pyright: ignore[reportAny]

    # labeled = label_img_fastest(img, color_table)
    labeled = label_img_fastest_uint16(image, color_table)
    values: list[int] = []

    # print()
    # print(f"image : {image.shape} px of type {image.dtype}")
    # print(f"labels :\n{labels}")
    # print(f"color_table :\n{color_table}")

    im_id = random.randint(0, 65536)

    for i, settings in enumerate(det_params):
        j = i + 1  # 0 is the bg
        if j not in labels:
            # skip unused labels
            values.append(0)
            continue
        detector = cv.SimpleBlobDetector.create(settings.load_params(len(color_table)))
        isolated_color = isolate_categories(color_table, [j])

        print(isolated_color)

        gs_palette = evenly_spaced_gray_palette(isolated_color)

        print(gs_palette)

        gs_img = gs_palette[labeled.flatten()]
        gs_img = gs_img.reshape(image.shape[:2]).astype(np.uint8)

        key_points = detector.detect(gs_img)
        values.append(len(key_points))


        if debug == -1:
            mat = visualize_detection(image, gs_img, key_points)
            cv.imshow("visualisation", mat)
            cv.imshow("gs_img", gs_img)
            _ = cv.waitKey(0)
            print("debug_print:",cv.imwrite("/Users/louis/Desktop/debug_out.png", mat))

        if debug >= 1:
            kp = cv.drawKeypoints(
                gs_img,
                key_points,
                np.array(None),
                [0, 0, 255],
                RICH_KEYPOINTS,
            )
            _ = cv.imwrite(expand_debug(f"col{j}_kp_km_{im_id}.jpg"), kp)
            _ = cv.imwrite(expand_debug(f"col{j}_gs_km_{im_id}.jpg"), gs_img)

    if debug >= 1:
        _ = cv.imwrite(expand_debug(f"crop_km_{im_id}.jpg"), image)
    if debug >= 3:
        _ = cv.imwrite(expand_debug(f"labled_km_{im_id}.png"), labeled)

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

        values = count_spots_fourth_method(image_16, color_table, config.det_params, debug=0)
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
