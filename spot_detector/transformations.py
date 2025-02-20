# Python standard library
from time import perf_counter
import cv2 as cv
import numpy as np
from numpy.typing import NDArray
from scipy import signal

# Project files
from .types import T


def crop_to_main_circle(src: NDArray, print_debug: bool = False) -> NDArray:
    # TODO: Make it not as dumb !!!
    if len(src.shape) == 3:
        # TODO: Get rid of this ???
        # gray = diff_of_gaussian(src[:, :, 0], 10, 50)
        gray = cv.cvtColor(src, cv.COLOR_BGR2GRAY)
        if print_debug:
            cv.imshow("DEBUG", gray)
            cv.waitKey(0)
    else:
        gray = src
    circles = None

    # Debug variables
    iter_count: int = 0
    p1_spy: int = 0
    p2_spy: int = 0

    for p2 in range(300, 100, -50):
        for p1 in range(100, 40, -10):
            iter_count += 1
            p1_spy = p1
            p2_spy = p2
            circles = cv.HoughCircles(
                gray,
                cv.HOUGH_GRADIENT,
                dp=4,
                minDist=100,
                param1=p1,
                param2=p2,
                minRadius=1000,
                maxRadius=1500,
            )
            if circles is not None:
                break
            # print(">", end='')
        if circles is not None:
            break
        # print("_", end='')
    if circles is None:
        if print_debug:
            print("Can't find circle: I give up")
        return src
    else:
        if print_debug:
            print("found main circle after", iter_count, "attempts.")
            print("p1 and p2 have values", p1_spy, "and", p2_spy)
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
    dist_squared = (coords**2).sum(axis=0)
    mask = dist_squared <= radius**2
    output = src[top:bottom, left:right, :] * mask[:, :, None]
    return output


def isolate_categories(
    color_table: NDArray, categories: list[int]
) -> NDArray[np.uint8]:
    color: NDArray[np.uint8] = np.uint8(color_table[:, 0:3].copy())  # type: ignore
    for i in range(color_table.shape[0]):
        if color_table[i, 3] not in categories:
            color[i, :] = 0
    return color


def label_img_fastest(im: NDArray, color_table: NDArray) -> NDArray:
    """
    Broadcasting is necessary to iterate over each shade.
    ┌──────────┬───────────┬───────────┬───────────┬───────────┐
    │ axes     │     0     │     1     │     2     │     3     │
    ╞══════════╪═══════════╪═══════════╪═══════════╪═══════════╡
    │col table │   shade   │     4     │    -/-    │    -/-    │
    │->palette │     1     │     1     │   shade   │     3     │
    ├──────────┼───────────┼───────────┼───────────┼───────────│
    │ im       │     Y     │     X     │     3     │    -/-    │
    │->im      │     Y     │     X     │     1     │     3     │
    └──────────┴───────────┴───────────┴───────────┴───────────┘
    """
    palette = color_table[None, None, :, 0:3].astype(np.float32)
    im = im[:, :, None, :].astype(np.float32)
    """
    Now Both palette and im have broadcastable shapes.
    ┌──────────┬───────────┬───────────┬───────────┬───────────┐
    │ palette  │     1     │     1     │  [shade]  │    -3-    │
    │ im       │    [Y]    │    [X]    │     1     │    -3-    │
    └──────────┴───────────┴───────────┴───────────┴───────────┘
    which allows us to compute the distance between to bgr colors.
    ┌──────────┬───────────┬───────────┬───────────┐
    │ norm     │     Y     │     X     │  shades   │
    └──────────┴───────────┴───────────┴───────────┘
    """
    norm = np.linalg.norm(im - palette, axis=3)
    """
    And get the index of the lowest along axis 2 as value
    ┌──────────┬───────────┬───────────┐
    │ labeled  │     Y     │     X     │
    └──────────┴───────────┴───────────┘
    """
    labeled = norm.argmin(axis=2).astype(np.uint8)
    return labeled


def get_k_means(
    img: NDArray[np.uint8 | np.uint16],
    k: int,
    epsilon: float = 1e-4,
    max_iter: int = 60,
) -> tuple[NDArray, NDArray, NDArray]:
    """
    A function using OpenCV's kmeans function with extra steps
    returns:
    - the lookup table (LUT) associating each label from 0 to k-1 (1st index)
      with BGR values (2nd index). The BGR values are coded on 3x8 or 3x16 bits,
      depending the image's datatype)
    - the image, palettized with the LUT
    - the labeled image (the pixel value is replaced with indices to the LUT)

    """
    original_dtype = img.dtype
    if original_dtype not in (np.uint8, np.uint16):
        raise NotImplementedError
    flags = 0
    if epsilon:
        flags |= cv.TERM_CRITERIA_MAX_ITER
    if max_iter:
        flags |= cv.TERM_CRITERIA_EPS
    criteria = (flags, max_iter, epsilon)
    x, y, _ = img.shape
    points: NDArray = img.reshape((x * y, 3)).astype(np.float32)
    # noinspection PyTypeChecker
    _, labels, LUT = cv.kmeans(
        points,
        k,
        None,  # type: ignore
        criteria,
        1,
        cv.KMEANS_PP_CENTERS,
    )
    LUT = LUT.astype(original_dtype)
    output = LUT[labels.flatten()].reshape(img.shape)
    return LUT, output, labels


def gaussian_kernel(
    sigma: float,
    kernel_size: int,
) -> NDArray:
    if kernel_size < 0:
        kernel_size = -kernel_size
    if kernel_size % 2 == 0:
        kernel_size += 1
    indices = np.indices((kernel_size, kernel_size), dtype=float)
    coords = indices - (kernel_size - 1) / 2
    dist_squared = np.power(coords, 2).sum(axis=2)
    _1_2s = 1 / (2 * sigma)
    kernel = np.exp(-dist_squared * _1_2s) * (_1_2s / np.pi)
    return kernel


def laplacian_of_gaussian(
    img: NDArray,
    sigma: float,
    kernel_size: int,
) -> NDArray:
    kernel = gaussian_kernel(sigma, kernel_size)
    filtered = signal.convolve2d(img, kernel)
    sobel_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
    laplacian = signal.convolve2d(filtered, sobel_kernel)
    return laplacian * sigma


def chg_domain(
    img: NDArray,
    new_domain: tuple[float, float],
) -> NDArray:
    # noinspection PyArgumentList
    mini_p, maxi_p = img.min(), img.max()
    mini_n, maxi_n = new_domain
    coef = (maxi_n - mini_n) / (maxi_p - mini_p)
    new_img = (img - mini_p) * coef + mini_n
    return new_img


def unique_values(values: list[T] | NDArray) -> list[T]:
    acc = []
    for e in values:
        if e not in acc:
            acc.append(e)
    return acc


def evenly_spaced_gray_palette(palette: NDArray) -> NDArray:
    lum = np.array([0.0722, 0.7152, 0.2126])
    new_palette = np.sum(palette * lum, axis=1)
    current_shades, new_shades = evenly_spaced_values(new_palette)
    output_palette = new_palette.copy()
    for i, shade in enumerate(new_palette):
        for j, cur_shade in enumerate(current_shades):
            if shade == cur_shade:
                output_palette[i] = new_shades[j]
                break
    return output_palette.astype(np.uint8)


def evenly_spaced_values(gs_palette: NDArray) -> NDArray:
    u_vals = sorted(unique_values(gs_palette))
    u_vals = np.array(u_vals)
    index = np.arange(u_vals.size)
    index = np.round(index * 255 / (index.size - 1))
    return np.array([u_vals, index])
