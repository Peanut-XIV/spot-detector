# Python standard library
from pathlib import Path
from time import perf_counter, sleep
from multiprocessing import Queue, Process, parent_process
from typing import Union
# Project files
from .config import DetParams, ColorAndParams
from .types import DataElement, ImageElement
from .transformations import (
        diff_of_gaussian,
        crop_to_main_circle,
        keep_green_cyan,
        keep_red_yellow,
        setup_green_params,
        setup_orange_params,
        setup_green_params_faster,
        setup_orange_params_faster,
        label_img_fastest,
        isolate_categories,
        evenly_spaced_gray_palette,
)
# Other
from numpy.typing import NDArray
import numpy as np
import cv2 as cv
from cv2 import DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS as RICH_KEYPOINTS


# Obsolete
def count_spots_first_method(_path: str | Path,
                             debug: int = 0,
                             ) -> tuple[int, int]:
    _path = str(_path)
    original = cv.imread(_path)  # Pixel format is BGR
    print("|", end='')
    original = crop_to_main_circle(original)
    print("|", end='')
    hls = cv.cvtColor(original, cv.COLOR_BGR2HLS_FULL)
    hue = hls[:, :, 0]
    lightness = hls[:, :, 1]
    # process orange
    orange_part =\
        diff_of_gaussian(lightness, 1, 15) * keep_red_yellow(hue)
    detector = cv.SimpleBlobDetector.create(setup_orange_params())
    orange_keypoints = detector.detect(orange_part)
    print("|", end='')
    # process green
    green_part =\
        diff_of_gaussian(lightness, 5, 20) * keep_green_cyan(hue)
    detector = cv.SimpleBlobDetector.create(setup_green_params())
    green_keypoints = detector.detect(green_part)
    # Debug options
    if debug >= 1:
        cv.imwrite(expand_debug("Or_naive.jpg"),
                   cv.drawKeypoints(original, orange_keypoints,
                                    255, RICH_KEYPOINTS))
        cv.imwrite(expand_debug("Gr_naive.jpg"),
                   cv.drawKeypoints(original, green_keypoints,
                                    255, RICH_KEYPOINTS))
    return len(orange_keypoints), len(green_keypoints)


# Obsolete
def count_spots_second_method(_path: str | Path, color_table: NDArray):
    if isinstance(_path, Path):
        _path = str(_path)
    img = cv.imread(_path)  # Pixel format is BGR
    print("| Cropping ", end='')
    img = crop_to_main_circle(img)
    print("| Labeling ", end='')
    # load palette
    t0 = perf_counter()
    labeled_img = np.uint8(label_img_fastest(img, color_table))
    print(f"{perf_counter() - t0:.2f} ", end='')
    # make orange / green image
    print("| masking 1 ", end='')
    isolated_orange = isolate_categories(color_table, (1, 3))
    gs_orange_palette =\
        np.uint8(evenly_spaced_gray_palette(isolated_orange))
    gs_orange = gs_orange_palette[labeled_img.flatten()]
    gs_orange = gs_orange.reshape(labeled_img.shape)
    print("| masking 2 ", end='')
    isolated_green = isolate_categories(color_table, (2, 3))
    gs_green_palette = np.uint8(
            evenly_spaced_gray_palette(isolated_green))
    gs_green = gs_green_palette[labeled_img.flatten()]
    gs_green = gs_green.reshape(labeled_img.shape)
    # simple blob detector
    print("| detection 1 ", end='')
    detector = cv.SimpleBlobDetector.create(
        setup_orange_params_faster(gs_orange_palette.shape[0]))
    orange_kp = detector.detect(gs_orange)
    print("| detection 2 ", end='')
    detector = cv.SimpleBlobDetector.create(
        setup_green_params_faster(gs_green_palette.shape[0]))
    green_kp = detector.detect(gs_green)
    return len(orange_kp), len(green_kp)


# Obsolete
def count_spots_third_method(img: NDArray,
                             color_table: NDArray,
                             detectors: list,
                             ):
    img = crop_to_main_circle(img)
    labeled = label_img_fastest(img, color_table)
    values = []
    for i, detector in enumerate(detectors):
        if detector.empty():
            values.append(0)
            continue
        i += 1  # 0 is the bg
        isolated_color = isolate_categories(color_table, [i])
        gs_palette = evenly_spaced_gray_palette(isolated_color)
        gs_img = gs_palette[labeled.flatten()]
        gs_img = gs_img.reshape(labeled.shape)
        key_points = detector.detect(gs_img)
        values.append(len(key_points))
    return values


def count_spots_fourth_method(img: NDArray,
                              color_table: NDArray,
                              det_params: list[DetParams],
                              debug: int = 0,
                              ) -> list[int]:
    img = crop_to_main_circle(img)
    labeled = label_img_fastest(img, color_table)
    values = []
    for i, settings in enumerate(det_params):
        detector = cv.SimpleBlobDetector.create(
                load_params(settings, len(color_table)))
        j = i + 1  # 0 is the bg
        isolated_color = isolate_categories(color_table, [j])
        gs_palette = evenly_spaced_gray_palette(isolated_color)
        gs_img = gs_palette[labeled.flatten()]
        gs_img = np.uint8(gs_img.reshape(labeled.shape))
        key_points = detector.detect(gs_img)
        values.append(len(key_points))
        if debug >= 1:
            kp = cv.drawKeypoints(gs_img, key_points, None, [0, 0, 255],
                                  RICH_KEYPOINTS)
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


def load_params(det_params: DetParams,
                shades_count: int,
                ) -> cv.SimpleBlobDetector.Params:
    params = cv.SimpleBlobDetector.Params()
    params.blobColor = 255
    if shades_count != 0:
        thresh_step = 255 // shades_count
    else:
        thresh_step = 1
    if "min_dist" in det_params:
        params.minDistBetweenBlobs = det_params["min_dist"]
    thresh = det_params["thresh"]
    if thresh["automatic"]:
        params.minThreshold = thresh_step // 4
        params.maxThreshold = 255 - thresh_step // 4
        params.thresholdStep = thresh_step
    else:
        params.minThreshold = thresh["mini"]
        params.maxThreshold = thresh["maxi"]
        params.thresholdStep = thresh["step"]
    area = det_params["area"]
    if area["enabled"]:
        params.filterByArea = True
        params.minArea = area["mini"]
        if "maxi" in area:
            params.maxArea = area["maxi"]
    circ = det_params["circ"]
    if circ["enabled"]:
        params.filterByCircularity = True
        params.minCircularity = circ["mini"]
        if "maxi" in circ:
            params.maxCircularity = circ["maxi"]
    convex = det_params["convex"]
    if convex["enabled"]:
        params.filterByConvexity = True
        params.minConvexity = convex["mini"]
        if "maxi" in convex:
            params.maxConvexity = convex["maxi"]
    return params


def init_workers(count: int,
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
    # TODO create detectors from
    workers_list = []
    for i in range(count):
        worker = Process(
            target=img_processer,
            args=(in_queue, out_queue, config)
        )
        workers_list.append(worker)
    return workers_list


def img_processer(in_queue: Queue,
                  out_queue: Queue,
                  config: ColorAndParams,
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
    color_table = np.array(config["color_data"]["table"])
    parent = parent_process()
    while parent.is_alive():
        if in_queue.empty():
            sleep(1)
        else:
            job: Union[str, ImageElement] = in_queue.get()
            if job == "STOP":
                break
            folder_row, depth_col, path = job
            img = cv.imread(path)
            values = count_spots_fourth_method(img,
                                               color_table,
                                               config["det_params"])
            result: DataElement = (folder_row, depth_col, values)
            out_queue.put(result)
