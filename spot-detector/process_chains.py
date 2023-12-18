from image_process import *
from pathlib import Path
import cocos.numerics as cn
import cocos.device as cd
from file_utils import get_color_table_array


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
    gs_orange_palette = np.uint8(evenly_spaced_gray_palette(isolated_orange))
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
