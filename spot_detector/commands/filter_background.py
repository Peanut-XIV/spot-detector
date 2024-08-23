import click
import cv2
import numpy as np
from pathlib import Path

@click.command()
@click.argument("sigma_1", type=click.FLOAT)
@click.argument("sigma_2", type=click.FLOAT)
@click.option("-s", "--source", type=click.Path)
@click.option("-d", "--dest", type=click.Path)
def filter_background(sigma_1: float,
                      sigma_2: float,
                      source: str | None,
                      dest: str | None):
    if source is None:
        source_path = Path.cwd()
    else:
        source_path = Path(source)
    if dest is None:
        destination_path = source_path.joinpath("filtered")
        count = 0
        while destination_path.exists():
            if count > 99:
                raise IsADirectoryError(
                        "to many directories named \"filtered_xx\","
                        " please set the destination path manually"
                )
            destination_path = source_path.joinpath(f"filtered_{count}")
    else:
        destination_path = Path(dest)
        if destination_path.exists():
            raise IsADirectoryError(
                    "le chemin de destination indiqué existe déjà"
            )
    destination_path.mkdir()
    assert sigma_1 < sigma_2
    assert sigma_1 >= 0
    wheel_chars = ""
    wheel_count = 0
    for sub_dir in source_path.iterdir():
        dest_sub_dir = destination_path.joinpath(sub_dir.name)
        images = filter(is_image, sub_dir.iterdir())
        for img in images:
            print(f"{wheel_chars[wheel_count % 6]}", end="\r")
            wheel_count += 1
            source_cv2_mat = cv2.imread(str(img), cv2.IMREAD_COLOR + cv2.IMREAD_ANYDEPTH)
            if source_cv2_mat is None:
                print(f"failed to open image {str(img)}")
            source_mat = np.array(source_cv2_mat)
            source_type = source_mat.dtype
            k_size_1 = (int(sigma_1 * 4) + 1, int(sigma_1 * 4) + 1)
            k_size_2 = (int(sigma_2 * 4) + 2, int(sigma_2 * 4) + 1)
            blur_1 = cv2.GaussianBlur(source_mat, k_size_1, sigma_1, None, sigma_1, cv2.BORDER_DEFAULT)
            blur_2 = cv2.GaussianBlur(source_mat, k_size_2, sigma_2, None, sigma_2, cv2.BORDER_DEFAULT)
            blur_1 = np.array(blur_1).astype(np.int32)
            blur_2 = np.array(blur_2).astype(np.int32)
            dog = np.clip(blur_1 - blur_2, 0, None).astype(source_type)
            if not dest_sub_dir.exists():
                dest_sub_dir.mkdir()
            cv2.imwrite(str(dest_sub_dir.joinpath(img.name)), dog)


def is_image(path: Path) -> bool:
    exists = path.exists()
    file = path.is_file()
    img_ext = path.suffix.lower() in [".png", ".jpeg", ".jpg", ".tiff"]
    return bool(exists and file and img_ext)
