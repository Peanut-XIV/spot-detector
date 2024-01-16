# Python standard library
from pathlib import Path
from time import perf_counter
# Project files
from spot_detector.image_process import (
    crop_to_main_circle, diff_of_gaussian,
    keep_red_yellow, setup_orange_params, setup_orange_params_faster,
    keep_green_cyan, setup_green_params, setup_green_params_faster,
    label_img_fastest, isolate_categories, evenly_spaced_gray_palette,
)
import numpy as np
import cv2 as cv


def count_spots_first_method(_path: str | Path):
    if isinstance(_path, Path):
        _path = str(_path)
    original = cv.imread(_path)  # Pixel format is BGR
    print("|", end='')
    original = crop_to_main_circle(original)
    print("|", end='')
    hls = cv.cvtColor(original, cv.COLOR_BGR2HLS_FULL)
    hue = hls[:, :, 0]
    lightness = hls[:, :, 1]

    # process orange first
    orange_part =\
        diff_of_gaussian(lightness, 1, 15) * keep_red_yellow(hue)
    detector = cv.SimpleBlobDetector.create(setup_orange_params())
    orange_keypoints = detector.detect(orange_part)
    print("|", end='')

    # process green as well
    green_part =\
        diff_of_gaussian(lightness, 5, 20) * keep_green_cyan(hue)
    detector = cv.SimpleBlobDetector.create(setup_green_params())
    green_keypoints = detector.detect(green_part)

    return len(orange_keypoints), len(green_keypoints)


def count_spots_second_method(_path: str | Path, color_table):
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
    gs_green_palette = np.uint8(evenly_spaced_gray_palette(isolated_green))
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


def count_spots_third_method(img: np.ndarray,
                             color_table: np.ndarray,
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


def count_spots_fourth_method(img: np.ndarray,
                              color_table: np.ndarray,
                              det_params,
                              ):
    img = crop_to_main_circle(img)
    cv.imwrite("/Users/louis/Desktop/test/crop.jpg", img)
    labeled = label_img_fastest(img, color_table)
    cv.imwrite("/Users/louis/Desktop/test/labeled.jpg", labeled)
    values = []
    for i, settings in enumerate(det_params):
        detector = cv.SimpleBlobDetector.create(
                load_params(settings, len(color_table)))
        j = i + 1  # 0 is the bg
        isolated_color = isolate_categories(color_table, [j])
        gs_palette = evenly_spaced_gray_palette(isolated_color)
        gs_img = gs_palette[labeled.flatten()]
        gs_img = np.uint8(gs_img.reshape(labeled.shape))
        cv.imwrite(f"/Users/louis/Desktop/test/test{j}.jpg", gs_img)
        key_points = detector.detect(gs_img)
        values.append(len(key_points))
    return values


def load_params(det_params, shades_count):
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
