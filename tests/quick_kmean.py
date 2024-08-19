import cv2
import sys
from pathlib import Path
from spot_detector.transformations import get_k_means

if __name__ == "__main__":
    arguments = sys.argv
    src = Path(arguments[1])
    k = int(arguments[2])
    dest = Path(arguments[3])
    if src.is_file() and not dest.exists():
        imat = cv2.imread(str(src))
        _, output, _ = get_k_means(imat, k)
        cv2.imwrite(str(dest), output)
    else:
        print(
            "Error: src is file :", src.is_file(),
            ", dest exists :", dest.exists()
        )
