# Python standard library
from pathlib import Path
from time import perf_counter
# Project files
import spot_detector.image_process as proc
from spot_detector.config import DetParams
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
    original = proc.crop_to_main_circle(original)
    print("|", end='')
    hls = cv.cvtColor(original, cv.COLOR_BGR2HLS_FULL)
    hue = hls[:, :, 0]
    lightness = hls[:, :, 1]
    # process orange
    orange_part =\
        proc.diff_of_gaussian(lightness, 1, 15) * proc.keep_red_yellow(hue)
    detector = cv.SimpleBlobDetector.create(proc.setup_orange_params())
    orange_keypoints = detector.detect(orange_part)
    print("|", end='')
    # process green
    green_part =\
        proc.diff_of_gaussian(lightness, 5, 20) * proc.keep_green_cyan(hue)
    detector = cv.SimpleBlobDetector.create(proc.setup_green_params())
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
    img = proc.crop_to_main_circle(img)
    print("| Labeling ", end='')
    # load palette
    t0 = perf_counter()
    labeled_img = np.uint8(proc.label_img_fastest(img, color_table))
    print(f"{perf_counter() - t0:.2f} ", end='')
    # make orange / green image
    print("| masking 1 ", end='')
    isolated_orange = proc.isolate_categories(color_table, (1, 3))
    gs_orange_palette =\
        np.uint8(proc.evenly_spaced_gray_palette(isolated_orange))
    gs_orange = gs_orange_palette[labeled_img.flatten()]
    gs_orange = gs_orange.reshape(labeled_img.shape)
    print("| masking 2 ", end='')
    isolated_green = proc.isolate_categories(color_table, (2, 3))
    gs_green_palette = np.uint8(
            proc.evenly_spaced_gray_palette(isolated_green))
    gs_green = gs_green_palette[labeled_img.flatten()]
    gs_green = gs_green.reshape(labeled_img.shape)
    # simple blob detector
    print("| detection 1 ", end='')
    detector = cv.SimpleBlobDetector.create(
        proc.setup_orange_params_faster(gs_orange_palette.shape[0]))
    orange_kp = detector.detect(gs_orange)
    print("| detection 2 ", end='')
    detector = cv.SimpleBlobDetector.create(
        proc.setup_green_params_faster(gs_green_palette.shape[0]))
    green_kp = detector.detect(gs_green)
    return len(orange_kp), len(green_kp)


# Obsolete
def count_spots_third_method(img: NDArray,
                             color_table: NDArray,
                             detectors: list,
                             ):
    img = proc.crop_to_main_circle(img)
    labeled = proc.label_img_fastest(img, color_table)
    values = []
    for i, detector in enumerate(detectors):
        if detector.empty():
            values.append(0)
            continue
        i += 1  # 0 is the bg
        isolated_color = proc.isolate_categories(color_table, [i])
        gs_palette = proc.evenly_spaced_gray_palette(isolated_color)
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
    img = proc.crop_to_main_circle(img)
    labeled = proc.label_img_fastest(img, color_table)
    values = []
    for i, settings in enumerate(det_params):
        detector = cv.SimpleBlobDetector.create(
                load_params(settings, len(color_table)))
        j = i + 1  # 0 is the bg
        isolated_color = proc.isolate_categories(color_table, [j])
        gs_palette = proc.evenly_spaced_gray_palette(isolated_color)
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
