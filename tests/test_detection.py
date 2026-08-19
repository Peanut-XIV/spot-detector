from spot_detector.model.project import Project
from spot_detector.types import ImageRGB, CommonInt_T

import cv2 as cv
import numpy as np
import sys

from typing import cast

from spot_detector.processing.transformations import convert_mat_uint16
from spot_detector.processing.process_chains import count_spots_fourth_method


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("nope, need path")
        sys.exit(0)

    im_path = sys.argv[1]
    res = cv.imread(im_path, cv.IMREAD_COLOR_BGR | cv.IMREAD_ANYDEPTH)
    if res is None:
        print(f"{im_path} is not a valid image path")
        sys.exit(0)
    if not np.isdtype(res.dtype, np.uint16):
        print(f"{res.dtype} is not a valid dtype")
        sys.exit(0)
    res = cast(ImageRGB[CommonInt_T],res)
    int_im = convert_mat_uint16(res)


    config_path = sys.argv[2]
    project = Project.from_path(config_path)
    shades = np.array([row.as_row() for row in project.configuration.shades], dtype=np.uint16)


    out = count_spots_fourth_method(int_im, shades, project.configuration.det_params, debug=-1)
    print(out)
