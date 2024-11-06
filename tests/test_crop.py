import sys
from spot_detector.transformations import crop_to_main_circle
import cv2

def main(im_path):
    img = cv2.imread(im_path)
    if im_path is None:
        print("Error reading image")
        return
    output = crop_to_main_circle(img, True)
    cv2.imshow("Output", output)
    cv2.waitKey(0)
    return

if __name__ == "__main__":
    args = sys.argv
    if len(args) != 2:
        print("expected 1 path argument")
    main(args[1])
