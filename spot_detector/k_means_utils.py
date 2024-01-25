# Python standard library
from pathlib import Path
import csv
# Project files
from spot_detector.image_process import get_k_means
# other dependancies
import cv2 as cv
from numpy.typing import NDArray


class ImageView:
    def __init__(self,
                 img_shape: tuple[int],
                 is_alt_image: bool = False,
                 x: int = 0,
                 y: int = 0,
                 scale: int = 1,
                 ) -> None:
        self.width: int = img_shape[1]
        self.height: int = img_shape[0]
        self.is_alt_img: bool = is_alt_image

        x = 0 if x < 0 else x
        x = self.width if x > self.width else x
        self.x: int = x

        y = 0 if y < 0 else y
        y = self.height if y > self.height else y
        self.y: int = y

        scale = 1 if scale < 1 else scale
        scale = 32 if self.width//scale < 64 else scale
        self.scale: int = scale

    @property
    def scaled_width(self) -> int:
        return int(self.width // self.scale)

    @property
    def scaled_height(self) -> int:
        return int(self.height // self.scale)

    def zoom_in(self) -> None:
        if self.scaled_height > 64:
            self.scale *= 2
            self.move_right(5)
            self.move_down(5)

    def zoom_out(self) -> None:
        if self.scale > 1:
            self.scale /= 2
            self.move_up(2.5)
            self.move_left(2.5)

    def move_left(self, n: float = 1.) -> None:
        if self.x > 0:
            self.x -= int(self.scaled_width * 0.1 * n)
        if self.x < 0:
            self.x = 0

    def move_right(self, n: float = 1.) -> None:
        scaled_width = self.scaled_width
        if self.x + scaled_width < self.width:
            self.x += int(scaled_width * 0.1 * n)
        if self.x + scaled_width >= self.width:
            self.x = self.width - scaled_width

    def move_up(self, n: float = 1.) -> None:
        if self.y > 0:
            self.y -= int(self.scaled_height * 0.1 * n)
        if self.y < 0:
            self.y = 0

    def move_down(self, n: float = 1.) -> None:
        scaled_height = self.scaled_height
        if self.y + scaled_height < self.height:
            self.y += int(scaled_height * 0.1 * n)
        if self.y + scaled_height >= self.height:
            self.y = self.height - scaled_height

    def window_action(self, key: int):
        if key == ord(' '):
            self.is_alt_img = not self.is_alt_img
        elif key == ord('i'):
            self.zoom_in()
        elif key == ord('o'):
            self.zoom_out()
        elif key == ord('p'):
            self.scale = 1
        elif key == ord('q'):
            self.move_left()
        elif key == ord('d'):
            self.move_right()
        elif key == ord('z'):
            self.move_up()
        elif key == ord('s'):
            self.move_down()
        return self


def reshape_image(img: NDArray, img_view: ImageView) -> NDArray:
    if img_view.scale == 1:
        return img
    crop: NDArray = img[img_view.y: img_view.y + img_view.scaled_height,
                        img_view.x: img_view.x + img_view.scaled_width]
    try:
        reshaped = cv.resize(crop,
                             None,
                             None,
                             img_view.scale,
                             img_view.scale,
                             cv.INTER_NEAREST)
    except cv.error as e:
        new_error = cv.error(
                f"\nIMAGE: shape = {crop.shape}, type = {crop.dtype}"
                f"\nCROP:  shape = {crop.shape}, type = {crop.dtype}")
        raise new_error from e
    return reshaped


def run_gui(labeled_img: NDArray, palette: NDArray) -> list[int]:
    ct_size = palette.shape[0]
    img_shape = [labeled_img.shape[0], labeled_img.shape[1], 3]
    index = 0
    image_view = ImageView(img_shape)
    color_categories = [-1] * ct_size
    highlighted_palette = palette.copy()
    highlighted_palette[index, :] = [0, 0, 255]
    img1 = palette[labeled_img.flatten()]
    img1 = img1.reshape(img_shape)
    img2 = highlighted_palette[labeled_img.flatten()]
    img2 = img2.reshape(img_shape)
    mem_index = index
    while index >= 0:
        if mem_index != index:
            highlighted_palette = palette.copy()
            highlighted_palette[index, :] = [0, 0, 255]
            img2 = highlighted_palette[labeled_img.flatten()]
            img2 = img2.reshape(img_shape)
            mem_index = index
        shown_img = img2 if image_view.is_alt_img else img1
        shown_img = reshape_image(shown_img, image_view)
        shown_img = draw_palette(shown_img,
                                 palette,
                                 index,
                                 color_categories)
        cv.imshow("palette tool", shown_img)
        key = cv.waitKey()
        image_view.window_action(key)
        index, color_categories = other_actions(key,
                                                index,
                                                ct_size,
                                                color_categories)
    return color_categories


def palette_maker() -> None:
    img = input_img()
    k = input_means()
    lut, _, labels = get_k_means(img, k)
    lut_size = lut.shape[0]
    index = 0
    image_view = ImageView(img.shape)
    color_categories = [-1] * lut_size
    lut2 = lut.copy()
    lut2[index, :] = [0, 0, 255]
    img1 = lut[labels.flatten()]
    img1 = img1.reshape(img.shape)
    img2 = lut2[labels.flatten()]
    img2 = img2.reshape(img.shape)
    mem_index = index
    while index >= 0:
        if mem_index != index:
            lut2 = lut.copy()
            lut2[index, :] = [0, 0, 255]
            img2 = lut2[labels.flatten()]
            img2 = img2.reshape(img.shape)
            mem_index = index
        shown_img = img2 if image_view.is_alt_img else img1
        shown_img = reshape_image(shown_img, image_view)
        shown_img = draw_palette(shown_img, lut, index, color_categories)
        cv.imshow("palette tool", shown_img)
        key = cv.waitKey()
        image_view.window_action(key)
        index, color_categories = other_actions(key,
                                                index,
                                                lut_size,
                                                color_categories)
    with open("data.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['blue', 'green', 'red', 'category'])
        for i in range(lut_size):
            writer.writerow(list(lut[i, :]) + [color_categories[i]])


def other_actions(key: int,
                  index: int,
                  max_index: int,
                  color_categories: list,
                  ) -> tuple[int, list]:
    if key == ord('a'):
        index = (index - 1) % max_index
    elif key == ord('e'):
        index = (index + 1) % max_index
    elif key == ord('0'):
        color_categories[index] = 0
    elif key == ord('1'):
        color_categories[index] = 1
    elif key == ord('2'):
        color_categories[index] = 2
    elif key == ord('3'):
        color_categories[index] = 3
    elif key == ord('_'):
        index = -1
    return index, color_categories


def draw_palette(img: NDArray,
                 lut: NDArray,
                 index: int,
                 color_categories: list,
                 ) -> NDArray:
    for i in range(lut.shape[0]):
        offset = 20 + i * 120
        if i == index:
            img[10: 130, offset - 10: offset + 110] = [255, 255, 255]
        img[20: 120, offset: offset + 100] = lut[i]
        cv.putText(img,
                   str(color_categories[i]),
                   (offset, 160),
                   cv.FONT_HERSHEY_DUPLEX,
                   2,
                   [255, 255, 255],
                   thickness=4)

    return img


def input_img() -> NDArray:
    _str = input("chemin de l'image : ")
    _path = Path(_str)
    if _str == "":
        return cv.imread('/Users/Louis/Desktop/test.JPG')
    if not _path.is_file():
        print(f"'{_path.stem}' n'est pas un fichier !\nFin de l'exécution.")
        quit()
    _image = cv.imread(str(_path))
    if _image is None:
        print(f"'{_path.stem}' n'est pas une image !\nFin de l'exécution.")
        quit()
    return _image


def input_means() -> int:
    _k = input("Nombre de moyennes : ")
    if _k == '':
        return 18
    try:
        _k = int(_k)
    except ValueError:
        print(f"{_k} n'est pas un entier !\nFin de l'exécution")
        quit()
    return _k


if __name__ == "__main__":
    palette_maker()
