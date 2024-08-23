from multiprocessing import Process, Queue, parent_process
from pathlib import Path
from time import sleep
from typing import Union

import cv2 as cv
import numpy as np
from numpy.typing import NDArray

from .config import ColorAndParams, ColorAndParamsTemplate, DetParamsTemplate
from .transformations import (
    crop_to_main_circle,
    evenly_spaced_gray_palette,
    isolate_categories,
    label_img_fastest,
)

from .types import DataElement, ImageElement
from tomlkit.items import Table

RICH_KEYPOINTS = cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS

def count_spots_fourth_method(
    img: NDArray,
    color_table: NDArray,
    det_params: list[DetParamsTemplate],
    debug: int = 0,
) -> list[int]:
    img = crop_to_main_circle(img)
    labeled = label_img_fastest(img, color_table)
    values = []
    for i, settings in enumerate(det_params):
        detector = cv.SimpleBlobDetector.create(
            load_params(settings, len(color_table))
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


def load_params(
    det_params: Table,
    shades_count: int,
) -> cv.SimpleBlobDetector.Params:
    params = cv.SimpleBlobDetector.Params()
    params.blobColor = 255
    if shades_count != 0:
        thresh_step = 255 // shades_count
    else:
        thresh_step = 1
    if "min_dist" in det_params:
        minimum_distance: float | int = det_params["min_dist"]  # pyright: ignore[reportAssignmentType]
        if minimum_distance > 0.0:
            params.minDistBetweenBlobs = det_params["min_dist"]  # pyright: ignore[reportAssignmentType, reportAttributeAccessIssue]
    thresh = det_params["thresh"]
    if thresh["automatic"]:  # pyright: ignore[reportIndexIssue]
        params.minThreshold = thresh_step // 4
        params.maxThreshold = 255 - thresh_step // 4
        params.thresholdStep = thresh_step
    else:
        params.minThreshold = thresh["mini"]  # pyright: ignore[reportIndexIssue]
        params.maxThreshold = thresh["maxi"]  # pyright: ignore[reportIndexIssue]
        params.thresholdStep = thresh["step"]  # pyright: ignore[reportIndexIssue]
    area = det_params["area"]
    if area["enabled"]:  # pyright: ignore[reportIndexIssue]
        params.filterByArea = True
        params.minArea = area["mini"]  # pyright: ignore[reportIndexIssue]
        if "maxi" in area:  # pyright: ignore[reportOperatorIssue]
            params.maxArea = area["maxi"]  # pyright: ignore[reportIndexIssue]
    circ = det_params["circ"]
    if circ["enabled"]:  # pyright: ignore[reportIndexIssue]
        params.filterByCircularity = True
        params.minCircularity = circ["mini"]  # pyright: ignore[reportIndexIssue]
        if "maxi" in circ:  # pyright: ignore[reportOperatorIssue]
            params.maxCircularity = circ["maxi"]  # pyright: ignore[reportIndexIssue]
    convex = det_params["convex"]
    if convex["enabled"]:  # pyright: ignore[reportIndexIssue]
        params.filterByConvexity = True
        params.minConvexity = convex["mini"]  # pyright: ignore[reportIndexIssue]
        if "maxi" in convex:  # pyright: ignore[reportOperatorIssue]
            params.maxConvexity = convex["maxi"]  # pyright: ignore[reportIndexIssue]
    return params


def init_workers(
    count: int,
    config: ColorAndParams,
    in_queue: Queue,
    out_queue: Queue,
) -> list[Process]:
    """
    Créée un ensemble d'objets `multiprocessing.Process` mais n'invoque pas
    leur méthode `.start()`.
          `count`: Le nombre de Process à créer.
    `color_table`: La table contenant les informations nécessaire pour
                 simplifier les images. C'est une liste de liste
                 d'entiers et pas un array numpy car la table doit
                 être pickleable.
       `in_queue`: L'objet qui apporte les ImageElements aux processus.
      `out_queue`: L'objet qui réccupère les données produites par les
                 processus.
         `return`: La liste des Process.
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
    config: Table,
) -> None:
    """
    La fonction qui attend les instructions et traites les `ImageElements` qui
    lui sont transmis par la `in_queue` et renvoie le résultat par la
    `out_queue`.
       `in_queue`: L'objet `multiprocessing.Queue` depuis lequel arrive les
                 les `ImageElements`.
      `out_queue`: L'objet `multiprocessing.Queue` dans lequel les valeurs
                 calculées sont retournées.
    `color_table`: La table contenant les informations nécessaires pour
                 simplifier les images. C'est une liste de listes d'entiers
                 et pas un array Numpy car la table doit être pickleable.
         `return`: Rien.
    """
    color_table = np.array(config["color_data"]["table"])  # pyright: ignore[reportIndexIssue]
    parent = parent_process()
    if parent is None:
        return
    while parent.is_alive():
        if in_queue.empty():
            sleep(1)
        else:
            job: Union[str, ImageElement] = in_queue.get()
            if job == "STOP":
                break
            folder_row, depth_col, path = job
            img = cv.imread(path)
            values = count_spots_fourth_method(
                img, color_table, config["det_params"]  # pyright: ignore[reportArgumentType]
            )
            result: DataElement = (folder_row, depth_col, values)
            out_queue.put(result)
