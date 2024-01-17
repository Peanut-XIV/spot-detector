# Python standard library
import string
from pathlib import Path
import csv
import re
# Other dependancies
import numpy as np


im_ext = re.compile(r".+\.(jpe?g|JPE?G|png|PNG)")


def is_im_file(obj: Path) -> bool:
    return bool(obj.is_file() and im_ext.match(obj.name))


def count_images(dir: Path) -> int:
    return sum(map(is_im_file, dir.iterdir()))


def check_img_count(expected: int,
                    dossiers: list[Path],
                    ) -> tuple[int, list[int]]:
    image_counts = list(map(count_images, dossiers))
    mismatches = len(list(filter(lambda n_im: n_im != expected, image_counts)))
    return mismatches, image_counts


# Not used
def get_color_table_array(path: str = "data_good.csv") -> np.ndarray:
    color_table = []
    with open(path, "r", newline='') as file:
        reader = csv.reader(file)
        for line in reader:
            color_table.append(line)
    # eliminate first row (labels) and last row if empty
    if color_table[-1] == [''] * len(color_table[0]):
        color_table = color_table[1: -1]
    else:
        color_table = color_table[1:]
    color_table = map(lambda L: list(map(int, L)), color_table)
    color_table = np.array(list(color_table))
    return color_table


# Obsolete
def get_unprocessed_directories(csv_path: str | Path,
                                main_dir: str | Path,
                                ) -> tuple[bool, list[Path]]:
    if not Path(csv_path).exists():
        dirs = [subd for subd in Path(main_dir).iterdir() if subd.is_dir()]
        return False, dirs
    processed_directories = []
    csv_exists = False
    if Path(csv_path).exists():
        csv_exists = True
        with open(csv_path, "r", newline='') as tableur:
            reader = csv.reader(tableur)
            reader.__next__()
            reader.__next__()
            processed_directories = [ligne[0] for ligne in reader]

    unprocessed_directories = []
    for e in Path(main_dir).iterdir():
        if e.is_dir() and e.name not in processed_directories:
            unprocessed_directories.append(e)
    unprocessed_directories.sort()
    return csv_exists, unprocessed_directories


def match_dir_items(dir: str | Path,
                    pattern: str,
                    inserted_value: str,
                    ) -> list[Path]:
    pattern = string.Template(pattern)
    pattern = pattern.substitute(value=re.escape(inserted_value))
    regex = re.compile(pattern)
    dir = Path(dir)
    return list(filter(lambda x: regex.fullmatch(x.name), dir.iterdir()))
