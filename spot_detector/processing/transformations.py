# Python standard library
from math import sqrt
from typing import cast

# Third party imports
import cv2 as cv
from cv2.typing import MatLike
import numpy as np
from numpy import dtype, float32, float64, ndarray, uint8, uint16, uint32, uint64
from numpy.typing import NDArray

from spot_detector.types import Array2D, Bool2D, ShadeTable, ImageRGB, CommonInt_T, NVec, ShapeType, LabelTable


def convert_mat_uint16[S: ShapeType](mat: ndarray[S, dtype[CommonInt_T]]) -> ndarray[S, dtype[uint16]]:
    data_type = mat.dtype
    if np.isdtype(data_type, np.uint8):
        copy = np.bitwise_left_shift(mat.astype(uint16), 8).astype(uint16)
    elif np.isdtype(data_type, np.uint16):
        copy = mat.copy().astype(uint16)
    elif np.isdtype(data_type, np.uint32):
        copy = np.bitwise_right_shift(mat, 8).astype(uint16)
    elif np.isdtype(data_type, np.uint64):
        copy = np.bitwise_right_shift(mat, 24).astype(uint16)

    elif np.isdtype(data_type, np.int8):
        unsigned = np.bitwise_xor(mat, uint8(0x80)).astype(uint8)
        copy = np.bitwise_left_shift(mat, 8).astype(uint16)
    elif np.isdtype(data_type, np.int16):
        copy = np.bitwise_xor(mat, uint16(0x8000)).astype(uint16)
    elif np.isdtype(data_type, np.int32):
        unsigned = np.bitwise_xor(mat, uint32(0x80000000)).astype(uint32)
        copy = np.bitwise_right_shift(unsigned, 16).astype(uint16)
    elif np.isdtype(data_type, np.int64):
        unsigned = np.bitwise_xor(mat, uint64(0x8000000000000000)).astype(uint64)
        copy = np.bitwise_right_shift(unsigned, 48).astype(uint16)

    else:
        raise TypeError("Unsupported datatype for argument mat. Datatype must be an integer type")

    copy = cast(ndarray[S, dtype[uint16]], copy)

    return copy

def convert_mat_uint8[S: ShapeType](mat: ndarray[S, dtype[CommonInt_T]]) -> ndarray[S, dtype[uint8]]:

    # cast to U8 :
    match mat.dtype:

        case np.uint8:
            copy = mat.copy().astype(uint8)
        case np.uint16:
            copy = np.bitwise_right_shift(mat, 8).astype(uint8)
        case np.uint32:
            copy = np.bitwise_right_shift(mat, 24).astype(uint8)
        case np.uint64:
            copy = np.bitwise_right_shift(mat, 56).astype(uint8)

        case np.int8:
            copy = np.bitwise_xor(mat, uint8(0x80)).astype(uint8)
        case np.int16:
            unsigned = np.bitwise_xor(mat, uint16(0x8000)).astype(uint16)
            copy = np.bitwise_right_shift(unsigned, 8).astype(uint8)
        case np.int32:
            unsigned = np.bitwise_xor(mat, uint32(0x80000000)).astype(uint32)
            copy = np.bitwise_right_shift(unsigned, 24).astype(uint8)
        case np.int64:
            unsigned = np.bitwise_xor(mat, uint64(0x8000000000000000)).astype(uint64)
            copy = np.bitwise_right_shift(unsigned, 56).astype(uint8)

        case _:
            raise TypeError("Unsupported datatype for argument mat. Datatype must be an integer type")

    copy = cast(ndarray[S, dtype[uint8]], copy)

    return copy



def compute_dish_ROI_mask(
    img: ImageRGB[CommonInt_T],
    radius_range: tuple[int, int] = (-1, -1),
    subsample_rate: int = 16,
    initial_threshold: int = 16,
    threshold_step: int = 16,
    minDist: int = 100,
) -> tuple[Bool2D, tuple[float, float, float]] | None:
    ss_rate = max(int(sqrt(subsample_rate)), 1)
    sub = img[::ss_rate, ::ss_rate, :3]

    dims = img.ndim
    gray: Array2D[CommonInt_T]
    if dims == 3:
        gray = cv.cvtColor(sub, cv.COLOR_BGR2GRAY)  # pyright: ignore[reportAssignmentType]
    elif dims == 2:
        gray = sub
    else:
        raise ValueError("Unsupported image array shape")

    try:
        gray = convert_mat_uint8(gray)
    except TypeError:
        raise TypeError("Unsupported floating point tiff image datatype")


    h, w = int(gray.shape[0]), int(gray.shape[1])
    small_edge = min(h,w)

    ideal_radius = small_edge/2

    small_radius = ideal_radius * 0.7 if radius_range[0] < 0 else radius_range[0] / ss_rate
    big_radius   = ideal_radius * 1.1 if radius_range[1] < 0 else radius_range[1] / ss_rate

    kernel = np.array(
        [
            [0, 1, 1, 1, 0],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [0, 1, 1, 1, 0],
        ],
        dtype=uint8,
    )

    candidates = np.empty(0)
    for thresh in range(initial_threshold, 256, threshold_step):
        _, binary = cv.threshold(gray, thresh, 255, cv.THRESH_BINARY)
        opened = cv.morphologyEx(binary, cv.MORPH_OPEN, kernel)
        closed = cv.morphologyEx(opened, cv.MORPH_CLOSE, kernel)
        grad = cv.morphologyEx(closed, cv.MORPH_GRADIENT, kernel)

        candidates = cv.HoughCircles(
            image=grad,
            method=cv.HOUGH_GRADIENT,  # simplest of the two
            dp=2,
            minDist=minDist/ss_rate,
            param1=128,  # our image is binary... no need to fine tune?
            param2=0.8,  # our processing causes jagged edges
            minRadius=int(small_radius),  # we expect the Petri dish to
            maxRadius=int(big_radius),  # occupy as much of the frame
        )

        if candidates is None or len(candidates) == 0:
            print(f"failed with threshold {thresh}")
        else:
            break

    if candidates is None or len(candidates) == 0:
        print("failed to crop image")
        return None

    coords: tuple[float, float, float] = candidates[0, 0, :] * ss_rate  # pyright: ignore[reportAssignmentType]
    x, y, r = coords

    mask: Bool2D = cv.circle(
        np.zeros((h, w), dtype=np.uint8),
        (int(x), int(y)),
        int(r),
        255,
        -1,
        cv.FILLED,
    ).astype(np.bool)

    return mask, coords




def crop_to_dish_roi(
    img: ImageRGB[CommonInt_T],
    radius_range: tuple[int, int] = (-1, -1),
    subsample_rate: int = 16,
    initial_threshold: int = 16,
    threshold_step: int = 16,
    minDist: int = 100,
) -> ImageRGB[CommonInt_T]:
    """
    Detects the visible circle of a petri dish within an image, based on some
    assumptions on its content, position, environment and lighting conditions.
    This algorithm simplifies the image with a given binary threshold value
    and applies morphological operations on it. The result is then fed to
    openCV's `HoughCirles` and evaluates the first candidate.

    Params
    ----
    img:
        an image, rgb or grayscale, any depth.

    radius_range:
        range of possible values in pixel for the radius of the circle to find.
        The smaller the faster. If left as (-1, -1), the range will be between
        70% to 110% of the radius of the largest circle that can fit in the image.

    subsample_rate:
        number by which the pixel count of the image is reduced.
        For example, 16 samples 1 in 4 pixels both verticaly and horizontaly.
        Making the image to process 16x smaller. Should be a square number.
        If not, will be rounded down. Set it to 1 or less to detect the ROI
        from the unmodified picture.

    minimum_threshold:
        Sets the first value to use for the threshold filter.

    threshold_step:
        Sets the incrementation step of the threshold value, should the previous
        one fail to detect a satisfying circle.
    """

    out = compute_dish_ROI_mask(img, radius_range, subsample_rate, initial_threshold, threshold_step, minDist)

    if out is None:
        return img
    else:
        mask, coords = out

    x, y, r = coords
    min_y, max_y = max(0, int(y - r) + 1), min(int(y + r), img.shape[0])
    min_x, max_x = max(0, int(x - r) + 1), min(int(x + r), img.shape[1])

    crop = img[min_y:max_y, min_x:max_x, :]
    new_mask = mask[min_y:max_y, min_x:max_x]

    with_circle = crop & new_mask

    return with_circle


def isolate_categories(
    color_table: ShadeTable, categories: list[int]
) -> Array2D[uint8]:
    color: Array2D[uint8] = color_table[:, 0:3].astype(np.uint8)
    for i in range(color_table.shape[0]):
        if color_table[i, 3] not in categories:
            color[i, :] = 0
    return color


def label_img_fastest_uint8(im: ImageRGB[uint8], color_table: ShadeTable) -> NDArray[uint8]:
    """
    Broadcasting is necessary to iterate over each shade.
    ┌──────────┬───────────┬───────────┬───────────┬───────────┐
    │ axes     │     0     │     1     │     2     │     3     │
    ╞══════════╪═══════════╪═══════════╪═══════════╪═══════════╡
    │col table │  shades   │ [b,g,r,n] │    -/-    │    -/-    │
    ├──────────┼───────────┼───────────┼───────────┼───────────│
    │ palette  │     1     │     1     │  shades   │  [b,g,r]  │
    └──────────┴───────────┴───────────┴───────────┴───────────┘
    ┌──────────┬───────────┬───────────┬───────────┬───────────┐
    │ axes     │     0     │     1     │     2     │     3     │
    ╞══════════╪═══════════╪═══════════╪═══════════╪═══════════╡
    │ im       │   rows    │   cols    │  [b,g,r]  │    -/-    │
    ├──────────┼───────────┼───────────┼───────────┼───────────│
    │ reshaped │   rows    │   cols    │     1     │  [b,g,r]  │
    └──────────┴───────────┴───────────┴───────────┴───────────┘
    """
    palette = convert_mat_uint8(color_table)[None, None, :, 0:3].astype(np.float32)
    float_im = im[:, :, None, :].astype(np.float32)
    """
    Now Both palette and im have compatible shapes.
    ┌──────────┬───────────┬───────────┬───────────┬───────────┐
    │ palette  │     1     │     1     │   shades  │  [b,g,r]  │
    │ im       │   rows    │   cols    │     1     │  [b,g,r]  │
    └──────────┴───────────┴───────────┴───────────┴───────────┘
    which allows us to compute the distance between to bgr colors.
    ┌──────────┬───────────┬───────────┬───────────┐
    │ norm     │   rows    │   cols    │  shades   │
    └──────────┴───────────┴───────────┴───────────┘
    """
    norm = np.linalg.norm(float_im - palette, axis=3)
    """
    And get the index of the lowest distance along axis 2 as value
    ┌──────────┬───────────┬───────────┐
    │ labeled  │   rows    │   cols    │
    └──────────┴───────────┴───────────┘
    """
    labeled = norm.argmin(axis=2).astype(uint8)
    return labeled


def label_img_fastest_uint16(im: ImageRGB[uint16], color_table: ShadeTable) -> NDArray[uint8]:
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
    float_color_table: NDArray[float32] = color_table[None, None, :, 0:3].astype(np.float32)
    float_im: NDArray[float32] = im[:, :, None, :].astype(np.float32)
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
    norm: NDArray[float32] = np.linalg.norm(float_im - float_color_table, axis=3).astype(float32)
    """
    And get the index of the lowest along axis 2 as value
    ┌──────────┬───────────┬───────────┐
    │ labeled  │     Y     │     X     │
    └──────────┴───────────┴───────────┘
    """
    labeled: NDArray[uint8] = norm.argmin(axis=2).astype(uint8)
    return labeled


def get_k_means[DataType: uint8 | uint16](
    img: ImageRGB[DataType],
    k: int,
    epsilon: float = 1e-4,
    max_iter: int = 60,
) -> tuple[LabelTable[DataType], ImageRGB[DataType], NVec[uint8]]:
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

    flags = 0
    if epsilon:
        flags |= cv.TERM_CRITERIA_MAX_ITER
    if max_iter:
        flags |= cv.TERM_CRITERIA_EPS
    criteria = (flags, max_iter, epsilon)
    x, y, _ = img.shape
    points: NDArray[float32] = img.reshape((x * y, 3)).astype(np.float32)

    _compacity, labels, lut = cv.kmeans(
        points,
        k,
        cast(MatLike, cast(object, None)), # bestLabels should be able to take None as a value but doesn't
        criteria,
        1,
        cv.KMEANS_PP_CENTERS,
        None
    )
    labels = cast(NVec[uint8], labels)
    lut = cast(LabelTable[float32], lut)

    new_lut: LabelTable[DataType] = np.astype(lut, original_dtype)
    pix_array: Array2D[DataType] = new_lut[labels.flatten()]
    quantized_image: ImageRGB[DataType] = pix_array.reshape(img.shape)  # pyright: ignore[reportAssignmentType]
    return new_lut, quantized_image, labels


def chg_domain(
    img: NDArray[np.integer | np.floating],
    new_domain: tuple[float, float],
) -> NDArray[np.floating]:
    mini_p, maxi_p = img.min(), img.max()
    mini_n, maxi_n = new_domain
    coef = (maxi_n - mini_n) / (maxi_p - mini_p)
    new_img = (img - mini_p) * coef + mini_n
    return new_img

def unique_values[T: np.generic](values: list[T] | NDArray[T]) -> list[T]:
    acc: list[T] = []
    for e in values:
        if e not in acc:
            acc.append(e)
    return acc


def evenly_spaced_gray_palette[T: np.integer](palette: Array2D[T]) -> NVec[uint8]:
    """
    Outputs a palette of grayscale values with the same relative brightness order.
    """
    luminosity_weights: NVec[float64] = np.array([0.2126, 0.0722, 0.7152])
    grayscale_palette: NVec[float64] = np.sum(palette * luminosity_weights, axis=1)
    unique_original_values, rectified_values = evenly_spaced_values(grayscale_palette)
    output_palette: NVec[uint8] = np.zeros(grayscale_palette.shape, dtype=uint8)

    for i, shade in enumerate(grayscale_palette):
        for j, cur_shade in enumerate(unique_original_values):
            if shade == cur_shade:
                output_palette[i] = rectified_values[j]
                break

    return output_palette


def evenly_spaced_values[T: np.integer | np.floating](gs_palette: NDArray[T]) -> tuple[NVec[T], NVec[uint8]]:
    unique_original_values = np.unique_values(gs_palette)
    if len(unique_original_values) > 255:
        raise ValueError("Expected a maximum of 255 different shades")
    unique_original_values.sort()
    count = len(unique_original_values)
    indices = np.arange(count)
    rectified_values = np.round(indices * 255 / (count - 1)).astype(uint8)
    return (unique_original_values, rectified_values)
