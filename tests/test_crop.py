import sys
import os
from typing import Any, Literal
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
import cv2


from spot_detector.transformations import crop_to_dish_roi

KERNEL = np.array(
    [
        [0, 1, 1, 1, 0],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [0, 1, 1, 1, 0],
    ],
    dtype=np.uint8,
)


def to_uint8(img: NDArray[Any]) -> NDArray[np.uint8]:
    """
    negative values will be set to zero
    """
    dtype = img.dtype
    if isinstance(dtype, np.integer):
        if isinstance(dtype, np.signedinteger):
            ...

    return img.astype(np.uint8)


def to_unsigned_int(
    img: NDArray,
    domain_change: Literal["ReLU", "abs", "shift"] = "ReLU",
    lerp_float_first: bool = True,
) -> NDArray[np.unsignedinteger]:
    dtype = img.dtype
    if isinstance(dtype, np.unsignedinteger):
        return img

    img = img.copy()

    if lerp_float_first and (dtype == np.float32 or dtype == np.float64):
        return lerp_float_to_pos_int(img)

    match domain_change:
        case "ReLU":
            np.maximum(img, 0, img)
        case "abs":
            np.abs(img, img)
        case "shift":
            risks_overflow = False

            mini = min(img)
            if dtype not in [np.float32, np.float64]:
                min_allowed = np.iinfo(dtype).min
                if mini == min_allowed:
                    risks_overflow = True

            if risks_overflow:
                offset = np.abs(mini.astype(np.int64)).astype(np.uint64)
                img = img + offset.astype(dtype)
            else:
                offset = -mini
                np.add(img, offset.astype(dtype), img)

    dtype = img.dtype

    match dtype:
        case np.int8:
            return img.astype(np.uint8)
        case np.int16:
            return img.astype(np.uint16)
        case np.int32:
            return img.astype(np.uint32)
        case np.int64:
            return img.astype(np.uint64)
        case np.float32 | np.float64:
            return lerp_float_to_pos_int(img)
        case other:
            raise ValueError(f"Unexpected datatype: {other}")


def lerp_float_to_pos_int(img: NDArray):
    # only uint32 for float32 because they only have 23 mantissa bits
    out_type = np.uint64 if img.dtype == np.float64 else np.uint32
    out_maxi = np.iinfo(out_type).max
    mini = img.min()
    maxi = img.max()

    img = np.around(((img - mini) / (maxi - mini)) * out_maxi, 0)  # out_mini = 0
    return img.astype(out_type)


def to_grayscale(img: NDArray) -> NDArray:
    """
    transparency not handled
    """
    shape = img.shape
    dims = len(shape)

    if not 1 < dims < 4:
        raise ValueError(f"invalid number of dimensions in array: {dims}")

    if dims == 2:
        grayscale = img
    else:
        if shape[2] > 3:
            raise NotImplementedError("we don't handle images with 4 channels, sorry")
        grayscale = img.sum(axis=2) / img.shape[2]

    return grayscale


def main(im_path: str):
    src_dir = Path(im_path)
    src_dir_name = src_dir.name
    dest_dir_name = src_dir_name + "cropped"
    dest_dir = src_dir.parent / dest_dir_name

    if dest_dir.exists():
        print("the destination directory already exists, goodbye")
        sys.exit(0)

    os.mkdir(dest_dir)

    skips = 0
    fails = 0
    error = 0
    count = 0
    for src_path in src_dir.iterdir():
        count += 1
        if not src_path.is_file():
            skips += 1
            continue
        img = cv2.imread(str(src_path), cv2.IMREAD_ANYDEPTH + cv2.IMREAD_COLOR_BGR)

        if img is None:
            print(f"failed opening image {str(src_path)}")
            fails += 1
            continue

        dest_path = dest_dir / src_path.name

        try:
            new_img = crop_to_dish_roi(img)
            if new_img.shape == img.shape:
                fails += 1
            cv2.imwrite(str(dest_path), new_img)
        except Exception as e:
            error += 1
            print(f"an exception occured while processing image {src_path}: {e}")

    print(
        f"Done. Looked at {count} files, skipped {skips}, "
        f"failed to open {fails} and errored {error} times"
    )
    print(f"processed files were written to {str(dest_dir)}")


if __name__ == "__main__":
    # if test_my_function(to_unsigned_int):
    #     print("prelim test failed, goodbye")
    #     sys.exit(0)

    args = sys.argv
    if len(args) != 2 or not Path(args[1]).is_dir():
        print("expected 1 path argument")
        sys.exit(0)
    main(args[1])
    print("\a")
