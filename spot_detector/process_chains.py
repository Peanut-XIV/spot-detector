from multiprocessing import Process, Queue, parent_process
from pathlib import Path
from time import sleep
from typing import Union

import cv2 as cv
import numpy as np
from numpy.typing import NDArray

from .config import ColorAndParams, DetParams
from .transformations import (
    crop_to_main_circle,
    evenly_spaced_gray_palette,
    isolate_categories,
    label_img_fastest,
)

from .types import DataElement, ImageElement

RICH_KEYPOINTS = cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS

def count_spots_fourth_method(
    img: NDArray,
    color_table: NDArray,
    det_params: list[DetParams],
    debug: int = 0,
) -> list[int]:
    img = crop_to_main_circle(img)
    labeled = label_img_fastest(img, color_table)
    values = []
    for i, settings in enumerate(det_params):
        detector = cv.SimpleBlobDetector.create(
            settings.load_params(len(color_table))
        )
        j = i + 1  # 0 is the bg
        isolated_color = isolate_categories(color_table, [j])
        gs_palette = evenly_spaced_gray_palette(isolated_color)
        gs_img = gs_palette[labeled.flatten()]
        gs_img = gs_img.reshape(labeled.shape).astype(np.uint8)
        key_points = detector.detect(gs_img)
        values.append(len(key_points))
        if debug >= 1:
            kp = cv.drawKeypoints(
                gs_img,
                key_points,
                None, # type: ignore
                [0, 0, 255],
                RICH_KEYPOINTS
            )
            cv.imwrite(expand_debug(f"col{j}_kp_km.jpg"), kp)
            cv.imwrite(expand_debug(f"col{j}_gs_km.jpg"), gs_img)
    if debug >= 1:
        cv.imwrite(expand_debug("crop_km.jpg"), img)
    if debug >= 3:
        cv.imwrite(expand_debug("labled_km.png"), labeled)
    return values


def expand_debug(string: str) -> str:
    debug_path = Path.home().joinpath("Desktop/debug")
    return str(debug_path.joinpath(string))




def init_workers(
    count: int,
    config: ColorAndParams,
    in_queue: Queue,
    out_queue: Queue,
) -> list[Process]:
    """
    Creates a list of multiprocessing process objects but does not call
    their start method.
    :param count: The number of processes to create
    :param config: The configuration of the detector for each label
    :param in_queue: The queue from which the processes fetch their input data
    :param out_queue: The queue to which the processed data is output
    :return: The list of process objects
    """
    workers_list = []
    for _ in range(count):
        worker = Process(
            target=img_processer, args=(in_queue, out_queue, config)
        )
        workers_list.append(worker)
    return workers_list


def img_processer(
    in_queue: Queue,
    out_queue: Queue,
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
    color_table = np.array(config.color_data.table)
    parent = parent_process()
    if parent is None:
        return
    while parent.is_alive():
        if in_queue.empty():
            sleep(1)
        else:
            job: Union[str, ImageElement] = in_queue.get()
            if isinstance(job, str):
                if job == "STOP":
                    break
                else:
                    print("How? WHy?")
            else:
                folder_row, depth_col, path = job
                img = cv.imread(path)
                values = count_spots_fourth_method(
                    img, color_table, config.det_params
                )
                result: DataElement = (folder_row, depth_col, values)
                out_queue.put(result)
