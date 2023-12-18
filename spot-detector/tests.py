import cv2
import cv2 as cv
from cv2 import DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS as RICH_KEYPOINTS

import csv
from pathlib import Path
from time import perf_counter

from k_means_utils import input_img, input_means
from file_utils import get_color_table_array
from image_process import *


def disp_kp_and_save(img, key_points, file_name, color):
    output_path = "/Users/Louis/Desktop/détection de points/output/"
    # noinspection PyTypeChecker
    output_image = cv.drawKeypoints(img, key_points, None, color=color,
                                    flags=RICH_KEYPOINTS)
    cv.imshow("window", output_image)
    if cv.waitKey() == ord('s'):
        cv.imwrite(output_path + f"{file_name}.png", output_image)
    return output_image


def show_every_image_and_input_a_number(image_directory, file_path):
    img_dir = Path(image_directory)
    file_path = Path(file_path)
    
    checked_images = []
    if file_path.exists():
        with open(file_path, 'r', newline='') as table:
            reader = csv.reader(table, dialect='unix')
            for row in reader:
                checked_images.append(row[0])
    with open(file_path, 'a', newline='') as table:
        writer = csv.writer(table, dialect='unix')
        folders = sorted([e for e in img_dir.iterdir() if e.is_dir()])
        for folder in folders:
            images = sorted([e for e in folder.glob("*.JPG") if
                             e.is_file() and e.name not in checked_images])
            for image in images:
                img = crop_to_main_circle(cv.imread(str(image)))
                cv.imshow('window', img)
                cv.waitKey()
                spots_num = input(":")
                writer.writerow([image.name, spots_num])


def process_images_with_steps(_path: str | Path):
    etapes = "/Users/Louis/Desktop/etapes/"
    if isinstance(_path, Path):
        _path = str(_path)
    original = cv.imread(_path)
    cv.imwrite(f"{etapes}originale.png", original)
    original = crop_to_main_circle(original)
    cv.imwrite(f"{etapes}crop.png", original)
    hls = cv.cvtColor(original, cv.COLOR_BGR2HLS_FULL)
    hue = hls[:, :, 0]
    lightness = hls[:, :, 1]
    cv.imwrite(f"{etapes}hue.png", hue)
    cv.imwrite(f"{etapes}lightness.png", lightness)

    # process orange first
    orange_mask = keep_red_yellow(hue)
    cv.imwrite(f"{etapes}orange_mask.png", orange_mask * 255)
    dog_orange = diff_of_gaussian(lightness, 1, 15)
    cv.imwrite(f"{etapes}dog_orange.png", dog_orange)
    orange_part = dog_orange * orange_mask
    cv.imwrite(f"{etapes}orange_part.png", orange_part)
    detector = cv.SimpleBlobDetector.create(setup_orange_params())
    orange_keypoints = detector.detect(orange_part)
    # noinspection PyTypeChecker
    orange_output = cv.drawKeypoints(lightness, orange_keypoints,
                                     None, color=[0, 90, 255],
                                     flags=RICH_KEYPOINTS)
    cv.imwrite(f"{etapes}orange_output.png", orange_output)

    # process green as well
    green_mask = keep_green_cyan(hue)
    cv.imwrite(f"{etapes}green_mask.png", green_mask * 255)
    dog_green = diff_of_gaussian(lightness, 5, 20)
    cv.imwrite(f"{etapes}dog_green.png", dog_green)
    green_part = dog_green * green_mask
    cv.imwrite(f"{etapes}green_part.png", green_part)
    detector = cv.SimpleBlobDetector.create(setup_green_params())
    green_keypoints = detector.detect(green_part)
    # noinspection PyTypeChecker
    green_output = cv.drawKeypoints(lightness, green_keypoints,
                                    None, color=[255, 255, 0],
                                    flags=RICH_KEYPOINTS)
    cv.imwrite(f"{etapes}green_output.png", green_output)
    # noinspection PyTypeChecker
    full_output = cv.drawKeypoints(orange_output, green_keypoints,
                                   None, color=[255, 255, 0],
                                   flags=RICH_KEYPOINTS)
    cv.imwrite(f"{etapes}full_output.png", full_output)
    return len(orange_keypoints), len(green_keypoints)
    

def test_LoG():
    img = input_img()
    color_table = get_color_table_array()
    print(color_table)
    img_orange, img_green = extract_colors(img, color_table)
    print(img_orange.shape, img_orange.dtype)
    print(img_green.shape, img_green.dtype)
    gs_orange = cv.cvtColor(img_orange, cv.COLOR_BGR2GRAY)
    gs_green = cv.cvtColor(img_green, cv.COLOR_BGR2GRAY)
    detect_orange = laplacian_of_gaussian(gs_orange, 100, 505)
    detect_green = laplacian_of_gaussian(gs_green, 400, 2001)
    detect_orange = np.uint8(chg_domain(detect_orange, (0, 255)))
    detect_green = np.uint8(chg_domain(detect_green, (0, 255)))
    cv.imshow("window", detect_orange)
    cv.waitKey()
    cv.imwrite("/Users/Louis/Desktop/spot_detector_outputs/LoG_orange.png",
               detect_orange)
    cv.imshow("window", detect_green)
    cv.waitKey()
    cv.imwrite("/Users/Louis/Desktop/spot_detector_outputs/LoG_green.png",
               detect_green)
    cv.destroyAllWindows()


def test_local_maxima():
    # load img and palette
    img = input_img()
    img = crop_to_main_circle(img)
    color_table = get_color_table_array()
    labeled_img = label_img(img, color_table)
    # make green and orange palettes
    orange_palette = isolate_categories(color_table, (1, 3))
    green_palette = isolate_categories(color_table, (2, 3))
    orange_palette = np.uint8(evenly_spaced_gray_palette(orange_palette))
    green_palette = np.uint8(evenly_spaced_gray_palette(green_palette))
    # apply GS palettes to labeled img
    orange_gs = orange_palette[labeled_img.flatten()]
    orange_gs = orange_gs.reshape(labeled_img.shape)
    green_gs = green_palette[labeled_img.flatten()]
    green_gs = green_gs.reshape(labeled_img.shape)
    # simple blob detector
    cv.imshow("window", orange_gs)
    cv.waitKey()
    cv.imwrite("/Users/Louis/Desktop/spot_detector_outputs/orange_gs.png",
               orange_gs)
    cv.imshow("window", green_gs)
    cv.waitKey()
    cv.imwrite("/Users/Louis/Desktop/spot_detector_outputs/green_gs.png",
               green_gs)
    cv.destroyAllWindows()


def test_k_means():
    u_image = input_img()
    u_k = input_means()
    lut_, new_image_, _ = get_k_means(u_image, u_k)
    print(lut_)
    cv.imshow(f"{u_k} means", new_image_)
    cv.waitKey()
    cv.destroyAllWindows()


def test_crop(path):
    img = cv.imread(path)
    gray = diff_of_gaussian(img[:, :, 0], 10, 50)
    cv.imshow('window', gray)
    cv.waitKey()
    cv.imshow('window', crop_to_main_circle(img))
    cv.waitKey()


def test_second_method(_path: str | Path):
    start = perf_counter()
    output_path = '/Users/Louis/Desktop/detection_de_points/output/'
    if isinstance(_path, Path):
        _path = str(_path)
    img = cv.imread(_path)  # Pixel format is BGR
    cv.imwrite(output_path + "original.png", img)
    print("| Cropping ", end='')
    img = crop_to_main_circle(img)
    cv.imwrite(output_path + "cropped.png", img)
    print("| Labeling ", end='')
    # load palette
    # TODO: changer la manière de charger color_table
    color_table = get_color_table_array()
    t0 = perf_counter()
    labeled_img = np.uint8(label_img_fastest(img, color_table))
    print(f"{perf_counter() - t0:.2f} ", end='')
    cv.imwrite(output_path + "labeled.png", labeled_img)
    # make orange / green image
    print("| masking 1 ", end='')
    isolated_orange = isolate_categories(color_table, (1, 3))
    gs_orange_palette = np.uint8(evenly_spaced_gray_palette(isolated_orange))
    gs_orange = gs_orange_palette[labeled_img.flatten()]
    gs_orange = gs_orange.reshape(labeled_img.shape)
    cv.imwrite(output_path + "gs_orange.png", gs_orange)
    print("| masking 2 ", end='')
    isolated_green = isolate_categories(color_table, (2, 3))
    gs_green_palette = np.uint8(evenly_spaced_gray_palette(isolated_green))
    gs_green = gs_green_palette[labeled_img.flatten()]
    gs_green = gs_green.reshape(labeled_img.shape)
    cv.imwrite(output_path + "gs_green.png", gs_green)
    # simple blob detector
    print("| detection 1 ", end='')
    detector = cv.SimpleBlobDetector.create(
        setup_orange_params_faster(gs_orange_palette.shape[0]))
    orange_kp = detector.detect(gs_orange)
    print("| detection 2 ", end='')
    detector = cv.SimpleBlobDetector.create(
        setup_green_params_faster(gs_green_palette.shape[0])
    )
    green_kp = detector.detect(gs_green)
    print("| drawing ", end='')
    # noinspection PyTypeChecker
    with_kp = cv.drawKeypoints((img // 4).astype(np.uint8),
                               orange_kp,
                               None,
                               (0, 128, 255),
                               RICH_KEYPOINTS)
    # noinspection PyTypeChecker
    with_kp = cv.drawKeypoints(with_kp,
                               green_kp,
                               None,
                               (0, 255, 0),
                               RICH_KEYPOINTS)
    cv.imwrite(output_path + "kp.png", with_kp)
    # noinspection PyTypeChecker
    green_kp_img = cv.drawKeypoints(gs_green,
                                    green_kp,
                                    None,
                                    (0, 255, 0),
                                    RICH_KEYPOINTS)
    cv.imwrite(output_path + "green_kp.png", green_kp_img)
    # noinspection PyTypeChecker
    orange_kp_img = cv.drawKeypoints(gs_orange,
                                     orange_kp,
                                     None,
                                     (0, 128, 255),
                                     RICH_KEYPOINTS)
    cv.imwrite(output_path + "orange_kp.png", orange_kp_img)
    print(f"| {perf_counter() - start:.2f}")
    return len(orange_kp), len(green_kp)


def use_hal(array):
    array = cv.UMat(array)
    cv.ocl.Device.
    

if __name__ == "__main__":
    path_ = "/Users/Louis/Desktop/"\
            "detection_de_points/data/A6_2/A6_2 0.0-0.2.JPG"
    print(test_second_method(path_))
