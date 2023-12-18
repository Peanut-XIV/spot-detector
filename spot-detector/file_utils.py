import string
from pathlib import Path
import numpy as np
import csv
import re


def check_img_count(expected: int, dossiers: [Path]) -> (bool, list[int]):
    image_counts = [0] * len(dossiers)
    doesnt_match = False
    for i, folder in enumerate(dossiers):
        n = len([e for e in folder.iterdir() if e.is_file()])
        image_counts[i] = n
        if n != expected:
            doesnt_match = True
    return doesnt_match, image_counts


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
    color_table = map(lambda _list: list(map(int, _list)), color_table)
    color_table = np.array(list(color_table))
    return color_table


def get_unprocessed_directories(csv_path, main_dir):
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


def match_dir_items(directory: str | Path, pattern: str, inserted_value: str):
    full_pattern = string.Template(pattern)\
                         .substitute(value=re.escape(inserted_value))
    regex = re.compile(full_pattern)
    matching_items = []
    if isinstance(directory, str):
        directory = Path(directory)
    for item in directory.iterdir():
        if regex.fullmatch(item.name):
            matching_items.append(item)
    return matching_items
