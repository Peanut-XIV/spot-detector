# Python standard library
from math import sqrt
from typing import TypeAlias, TypeVar

# Third party imports
import cv2 as cv
import numpy as np
from numpy import int8, int16, int32, int64, uint8, uint16, uint32, uint64
from numpy.typing import NDArray


SignedIntegerType: TypeAlias = int8 | int16 | int32 | int64
UnsignedIntegerType: TypeAlias = uint8 | uint16 | uint32 | uint64
IntegerType: TypeAlias = SignedIntegerType | UnsignedIntegerType

def convert_mat_uint16(mat: NDArray[IntegerType]) -> NDArray[uint16]:
    match mat.dtype:

        case np.uint8:
            copy = np.bitwise_left_shift(mat.astype(uint16), 8).astype(uint16)
        case np.uint16:
            copy = mat.copy().astype(uint16)
        case np.uint32:
            copy = np.bitwise_right_shift(mat, 8).astype(uint16)
        case np.uint64:
            copy = np.bitwise_right_shift(mat, 24).astype(uint16)

        case np.int8:
            unsigned = np.bitwise_xor(mat, uint8(0x80)).astype(uint8)
            copy = np.bitwise_left_shift(mat, 8).astype(uint16)
        case np.int16:
            copy = np.bitwise_xor(mat, uint16(0x8000)).astype(uint16)
        case np.int32:
            unsigned = np.bitwise_xor(mat, uint32(0x80000000)).astype(uint32)
            copy = np.bitwise_right_shift(unsigned, 16).astype(uint16)
        case np.int64:
            unsigned = np.bitwise_xor(mat, uint64(0x8000000000000000)).astype(uint64)
            copy = np.bitwise_right_shift(unsigned, 48).astype(uint16)

        case _:
            raise TypeError("Unsupported datatype for argument mat. Datatype must be an integer type")

    return copy

def convert_mat_uint8(mat: NDArray[IntegerType]) -> NDArray[uint8]:

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

    return copy


T: TypeVar = TypeVar("T")

def crop_to_dish_roi(
    img: NDArray[IntegerType],
    radius_range: tuple[int, int] = (-1, -1),
    subsample_rate: int = 16,
    initial_threshold: int = 16,
    threshold_step: int = 16,
    minDist: int = 100,
) -> NDArray[IntegerType]:
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

    ss_rate = max(int(sqrt(subsample_rate)), 1)
    sub = img[::ss_rate, ::ss_rate, :3]

    dims = len(img.shape)
    if dims == 3:
        gray = cv.cvtColor(sub, cv.COLOR_BGR2GRAY)
    elif dims == 2:
        gray = sub
    else:
        raise ValueError("Unsupported image array shape")

    try:
        gray = convert_mat_uint8(gray)
    except TypeError:
        raise TypeError("Unsupported floating point tiff image datatype")


    h, w = int(gray.shape[0]), int(gray.shape[1])  # pyright: ignore[reportAny]
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

        if len(candidates) > 0:
            break
        else:
            print(f"failed with threshold {thresh}")

    if len(candidates) == 0:
        print("failed to crop image")
        return img

    x, y, r = candidates[0, 0, :] * ss_rate
    min_y, max_y = max(0, int(y - r) + 1), min(int(y + r), img.shape[0])
    min_x, max_x = max(0, int(x - r) + 1), min(int(x + r), img.shape[1])

    crop = img[min_y:max_y, min_x:max_x, :]
    new_center = (int(x - min_x), int(y - min_y))

    max_dtype = np.iinfo(img.dtype).max
    white = [max_dtype] * 3
    # fill outside of circle
    # TODO: check if works with dtypes other than uint8
    mask = cv.circle(
        np.zeros(crop.shape, crop.dtype),
        new_center,
        int(r),
        white,
        -1,
        cv.FILLED,
    )

    with_circle = cv.bitwise_and(crop, mask)

    return with_circle


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
) -> NDArray[uint8]:
    color: NDArray[uint8] = uint8(color_table[:, 0:3].copy())  # type: ignore
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
    palette = color_table[None, None, :, 0:3].astype(np.float32)
    im = im[:, :, None, :].astype(np.float32)
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
    norm = np.linalg.norm(im - palette, axis=3)
    """
    And get the index of the lowest distance along axis 2 as value
    ┌──────────┬───────────┬───────────┐
    │ labeled  │   rows    │   cols    │
    └──────────┴───────────┴───────────┘
    """
    labeled = norm.argmin(axis=2).astype(uint8)
    return labeled


def label_img_fastest_uint16(im: NDArray, color_table: NDArray) -> NDArray:
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
    labeled = norm.argmin(axis=2).astype(uint16)
    return labeled


def get_k_means(
    img: NDArray[uint8 | uint16],
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
    if original_dtype not in (uint8, uint16):
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
    return output_palette.astype(uint8)


def evenly_spaced_values(gs_palette: NDArray) -> NDArray:
    u_vals = sorted(unique_values(gs_palette))
    u_vals = np.array(u_vals)
    index = np.arange(u_vals.size)
    # if index.size <= 1:
    #     print("palette with 1 unique element...", index.shape)
    #     print("gs_palette", gs_palette)
    #     print("u_vals", u_vals)
    index = np.round(index * 255 / (index.size - 1))
    return np.array([u_vals, index])
