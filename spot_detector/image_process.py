# Python standard library
from time import perf_counter
import cv2 as cv
import numpy as np
from scipy import signal
from typing import TypeVar

T = TypeVar('T')


# Obsolete
def keep_red_yellow(array: np.ndarray) -> np.ndarray:
    """
    Makes a binary mask from the hue component of an image,
    coded from 0 to 255. The mask's pixels are of value 1
    where the hue is smaller than 120 or larger than 200.
    Otherwise, pixels are of value 0.
    :param array: uint8 ndarray of shape (x,y).
    :return: uint8 ndarray of shape (x,y) with values either 0 or 1.
    """
    return np.uint8(np.logical_or(np.less(array, 120),
                                  np.greater(array, 200)))


# Obsolete
def keep_green_cyan(array: np.ndarray) -> np.ndarray:
    """
    Makes a binary mask from the hue component of an image,
    coded from 0 to 255. The mask's pixels are of value 1
    where the hue is between 90 and 150. Otherwise, pixels are of value 0.
    :param array: uint8 ndarray of shape (x,y).
    :return: uint8 ndarray of shape (x,y) with values either 0 or 1.
    """
    return np.uint8(np.logical_and(np.greater(array, 90),
                                   np.less(array, 140)))


# Obsolete
def normalize(array: np.ndarray) -> np.ndarray:
    """
    Does a linear interpolation of the values of an array,
    in such a way that 0 is mapped to 0 and the maximum positive
    value is mapped to 255.
    :param array: uint8 ndarray of shape (x,y,z)
    :return:  uint8 ndarray of shape (x,y,z)
    """
    maximum = int(np.amax(array))
    if maximum == 0:
        return array
    k = 255 / maximum
    return np.uint8(np.multiply(array, k))


# Obsolete
def diff_of_gaussian(array: np.ndarray,
                     rad_in: float,
                     rad_out: float,
                     ) -> np.ndarray:
    """
    The Difference of an image with itself at two
    different gaussian blur strength. Used to eliminate
    details outside a defined spatial frequency range.
    :param array: ndarray
    :param rad_in:
    :param rad_out:
    :return:
    """
    matrix_in = [2 * round(rad_in) + 1, 2 * round(rad_in) + 1]
    matrix_out = [2 * round(rad_out) + 1, 2 * round(rad_out) + 1]
    blur_in = cv.GaussianBlur(np.int16(array), matrix_in, rad_in)
    blur_out = cv.GaussianBlur(np.int16(array), matrix_out, rad_out)
    diff = blur_in - blur_out
    output = np.uint8(np.multiply(diff, diff > 0))
    return output


# Obsolete
def setup_green_params() -> cv.SimpleBlobDetector.Params:
    params = cv.SimpleBlobDetector.Params()
    params.filterByArea = True
    params.minArea = 20
    params.filterByCircularity = True
    params.minCircularity = 0.01
    params.filterByConvexity = True
    params.minConvexity = 0.001
    params.blobColor = 255
    params.minThreshold = 10
    params.maxThreshold = 200
    params.thresholdStep = 1
    return params


# Obsolete
def setup_green_params_faster(
        shades_count: int) -> cv.SimpleBlobDetector.Params:
    thresh_step = 255 // (shades_count - 1)
    params = cv.SimpleBlobDetector.Params()
    params.filterByArea = True
    params.minArea = 10
    params.filterByCircularity = True
    params.minCircularity = 0.01
    params.filterByConvexity = True
    params.minConvexity = 0.1
    params.blobColor = 255
    params.minThreshold = thresh_step // 2
    params.maxThreshold = 255 - thresh_step // 2
    params.thresholdStep = thresh_step
    return params


# Obsolete
def setup_orange_params() -> cv.SimpleBlobDetector.Params:
    params = cv.SimpleBlobDetector.Params()
    params.filterByArea = True
    params.minArea = 1
    params.filterByCircularity = True
    params.minCircularity = 0.01
    params.filterByConvexity = True
    params.minConvexity = 0.01
    params.blobColor = 255
    params.minThreshold = 10
    params.maxThreshold = 200
    params.thresholdStep = 5
    params.minDistBetweenBlobs = 10
    return params


# Obsolete
def setup_orange_params_faster(
        shades_count: int) -> cv.SimpleBlobDetector.Params:
    thresh_step = 255 // shades_count
    params = cv.SimpleBlobDetector.Params()
    params.filterByArea = True
    params.minArea = 4
    params.maxArea = 800
    params.filterByCircularity = True
    params.minCircularity = 0.01
    params.filterByConvexity = True
    params.minConvexity = 0.2
    params.blobColor = 255
    params.minThreshold = thresh_step // 4
    params.maxThreshold = 255 - thresh_step // 4
    params.thresholdStep = thresh_step
    params.minDistBetweenBlobs = 0.5
    return params


def crop_to_main_circle(src: np.ndarray) -> np.ndarray:
    # TODO: Make it not as dumb !!!
    if len(src.shape) == 3:
        gray = diff_of_gaussian(src[:, :, 0], 10, 50)
    else:
        gray = src
    circles = None
    for p2 in range(300, 100, -50):
        for p1 in range(100, 40, -10):
            circles = cv.HoughCircles(gray, cv.HOUGH_GRADIENT, dp=4,
                                      minDist=100, param1=p1, param2=p2,
                                      minRadius=1000, maxRadius=1500)
            if circles is not None:
                break
            print(">", end='')
        if circles is not None:
            break
        print("_", end='')
    if circles is None:
        return src
    x, y, radius = circles[0][0]
    radius = round(radius * 1.05)
    x = round(x)
    y = round(y)

    # clip, in case the circle was not completely overlapping the source image
    left = max(0, x - radius)
    right = min(x + radius, src.shape[1] - 1)
    top = max(0, y - radius)
    bottom = min(y + radius, src.shape[0] - 1)

    # make a matrix with a shape fitting as much of the circle,
    # in the limit of the src dimensions
    offset = np.ndarray(shape=(2, 1, 1))
    offset[:, 0, 0] = (min(radius, y), min(radius, x))
    coords = np.indices((bottom - top, right - left)) - offset
    dist_squared = (coords ** 2).sum(axis=0)
    mask = dist_squared <= radius**2
    return src[top:bottom, left:right, :] * mask[:, :, None]


# Obsolete
def extract_colors(img: np.ndarray,
                   color_table: np.ndarray,
                   ) -> tuple[np.ndarray, np.ndarray]:
    color1 = isolate_categories(color_table, (1, 3))
    color2 = isolate_categories(color_table, (2, 3))
    labeled_img = label_img(img, color_table)
    mask1 = color1[labeled_img.flatten()]
    mask1 = mask1.reshape(img.shape)
    mask2 = color2[labeled_img.flatten()]
    mask2 = mask2.reshape(img.shape)
    return mask1, mask2


def isolate_categories(color_table: np.ndarray, categories: list[int]):
    color = np.uint8(color_table[:, 0:3].copy())
    for i in range(color_table.shape[0]):
        if color_table[i, 3] not in categories:
            color[i, :] = 0
    return color


def label_img(img: np.ndarray, color_table: np.ndarray) -> np.ndarray:
    table_size = color_table.shape[0]
    height, width = img.shape[0:2]
    delta_shape = (height, width, len(color_table))
    deltas = np.empty(shape=delta_shape)
    for i in range(table_size):
        print(f"{i}.", end='')
        diff = (img - color_table[i, 0:3])
        print(".", end='')
        diff_sq = diff ** 2
        print(".", end='')
        diff_sq_summed = np.sum(diff_sq, axis=2)
        deltas[..., i] = diff_sq_summed
    print("argmin ", end='')
    labeled_img = deltas.argmin(axis=2)
    return labeled_img


def label_img_faster(img: np.ndarray, color_table: np.ndarray) -> np.ndarray:
    t0 = perf_counter()
    palette = color_table[:, 0:3].astype(np.float32)
    pre_img = np.repeat(img[:, :, np.newaxis, :].astype(np.float32),
                        palette.shape[0], axis=2)
    labeled_img = np.linalg.norm(pre_img - palette, axis=-1).argmin(axis=-1)
    print(f"{perf_counter() - t0} ", end='')
    return labeled_img


def label_img_fastest(im: np.ndarray, color_table: np.ndarray) -> np.ndarray:
    """
    Broadcasting is necessary to iterate over each shade.
    |----------|-----------|-----------|-----------|-----------|
    | axes     |     0     |     1     |     2     |     3     |
    |==========|===========|===========|===========|===========|
    |col_table |   shade   |     4     |    -/-    |    -/-    |
    |->palette |     1     |     1     |   shade   |     3     |
    |----------|-----------|-----------|-----------|-----------|
    | im       |     Y     |     X     |     3     |    -/-    |
    |->im      |     Y     |     X     |     1     |     3     |
    |----------|-----------|-----------|-----------|-----------|
    """
    palette = color_table[None, None, :, 0:3].astype(np.float32)
    im = im[:, :, None, :].astype(np.float32)
    """
    Now Both palette and im have broadcastable shapes.
    |----------|-----------|-----------|-----------|-----------|
    | palette  |     1     |     1     |  [shade]  |    -3-    |
    | im       |    [Y]    |    [X]    |     1     |    -3-    |
    |----------|-----------|-----------|-----------|-----------|
    which allows us to compute the distance between to bgr colors.
    |----------|-----------|-----------|-----------|
    | norm     |     Y     |     X     |  shades   |
    |----------|-----------|-----------|-----------|
    """
    norm = np.linalg.norm(im - palette, axis=3)
    """
    And get the index of the lowest along axis 2 as value
    |----------|-----------|-----------|
    | labeled  |     Y     |     X     |
    |----------|-----------|-----------|
    """
    labeled = norm.argmin(axis=2).astype(np.uint8)
    return labeled


def label_img_ludicrous(im: np.ndarray, color_table: np.ndarray) -> np.ndarray:
    img = im.astype(np.float32)
    color_table = color_table.astype(np.float32)
    table_size = color_table.shape[0]
    height, width = img.shape[0:2]
    deltas = np.empty((height, width, table_size))
    for i in range(table_size):
        print(f"{i}.", end='')
        diff = cv.subtract(img, color_table[i, 0:3])
        print(".", end='')
        diff_sq = cv.pow(diff, 2)
        print(".", end='')
        diff_sq_summed = cv.reduce(diff_sq, 2, )
        deltas[..., i] = diff_sq_summed
    print("argmin ", end='')
    labeled_img = deltas.argmin(axis=2)
    return labeled_img


def get_k_means(img: np.ndarray,
                k: int,
                epsilon: float = 1e-4,
                max_iter: int = 60,
                ) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    flags = 0
    if epsilon:
        flags += cv.TERM_CRITERIA_MAX_ITER
    if max_iter:
        flags += cv.TERM_CRITERIA_EPS
    criteria = (flags, max_iter, epsilon)
    x, y, _ = img.shape
    points: np.ndarray = np.float32(img.reshape((x*y, 3)))
    # noinspection PyTypeChecker
    compactness, labels, LUT = cv.kmeans(points,
                                         k,
                                         None,
                                         criteria,
                                         1,
                                         cv.KMEANS_PP_CENTERS)
    LUT: np.ndarray = np.uint8(LUT)
    pre_output = LUT[labels.flatten()]
    output = pre_output.reshape(img.shape)
    return LUT, output, labels


def gaussian_kernel(sigma: float,
                    kernel_size: int,
                    ) -> np.ndarray:
    if kernel_size < 0:
        kernel_size = - kernel_size
    if kernel_size % 2 == 0:
        kernel_size += 1
    indices = np.indices((kernel_size, kernel_size), dtype=float)
    coords = indices - (kernel_size - 1) / 2
    dist_squared = np.power(coords, 2).sum(axis=2)
    _1_2s = 1 / (2 * sigma)
    kernel = np.exp(- dist_squared * _1_2s) * (_1_2s / np.pi)
    return kernel


def laplacian_of_gaussian(img: np.ndarray,
                          sigma: float,
                          kernel_size: int,
                          ) -> np.ndarray:
    kernel = gaussian_kernel(sigma, kernel_size)
    filtered = signal.convolve2d(img, kernel)
    sobel_kernel = np.array([[0, 1,  0],
                             [1, -4, 1],
                             [0, 1,  0]])
    laplacian = signal.convolve2d(filtered, sobel_kernel)
    return laplacian * sigma


def chg_domain(img: np.ndarray,
               new_domain: tuple[float, float],
               ) -> np.ndarray:
    # noinspection PyArgumentList
    mini_p, maxi_p = img.min(), img.max()
    mini_n, maxi_n = new_domain
    coef = (maxi_n - mini_n) / (maxi_p - mini_p)
    new_img = (img - mini_p) * coef + mini_n
    return new_img


def unique_values(values: list[T]) -> list[T]:
    acc = []
    for e in values:
        if e not in acc:
            acc.append(e)
    return acc


def evenly_spaced_gray_palette(palette: np.ndarray) -> np.ndarray:
    lum = np.array([0.0722, 0.7152, 0.2126])
    new_palette = np.sum(palette * lum, axis=1)
    current_shades, new_shades = evenly_spaced_values(new_palette)
    output_palette = new_palette.copy()
    for i, shade in enumerate(new_palette):
        for j, cur_shade in enumerate(current_shades):
            if shade == cur_shade:
                output_palette[i] = new_shades[j]
                break
    return np.uint8(output_palette)


def evenly_spaced_values(gs_palette: np.ndarray) -> np.ndarray:
    u_vals = sorted(unique_values(gs_palette))
    u_vals = np.array(u_vals)
    index = np.arange(u_vals.size)
    index = np.round(index * 255 / (index.size - 1))
    return u_vals, index
