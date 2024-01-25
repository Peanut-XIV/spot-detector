# Python standard library
from multiprocessing import Queue, Process
from pathlib import Path
import time
# Project files
from spot_detector.image_process import label_img_fastest
from spot_detector.file_utils import (read_csv, write_csv, fetch_csv,
                                      sorted_sub_dirs, unprocessed_images
                                      )
from spot_detector.k_means_utils import run_gui, get_k_means
from spot_detector.multi_core import init_workers
from spot_detector.config import (get_color_and_params,
                                  ColorAndParams,
                                  default_det_params,
                                  )
from spot_detector.types import DataRow, DataTable, DataElement
# Other
import numpy as np
import numpy.typing as npT
import tomlkit
import tomlkit.items as tomlItems
from tomlkit.toml_file import TOMLDocument, TOMLFile
import cv2 as cv
from click import echo


def count_categories(categories: list[int]) -> int:
    unique_categories = list(np.unique(np.array(categories)))
    return len(list(filter(lambda x: x > 0, unique_categories)))


def fill_data_points(table: DataTable,
                     data_points: DataElement,
                     depth_count: int,
                     color_count: int,
                     ) -> None:
    row, col, values = data_points
    for i, value in enumerate(values):
        table[row][1 + col + i * depth_count] = value
    table[row][1 + col + len(values) * depth_count] = sum(values)
    # Fill part1
    try_line_completion(table[row], depth_count, color_count)


def try_line_completion(current_row: DataRow,
                        depth_count: int,
                        color_count: int,
                        ) -> None:
    if "" in current_row[1: depth_count + 1]:
        return
    middle = 1 + (1 + color_count) * depth_count
    for i in range(color_count + 1):
        start = i * depth_count
        stop = start + depth_count
        part1 = current_row[1 + start: 1 + stop]
        sum1 = sum(map(int, part1))
        if sum1:
            part2 = [100 * int(v) / sum1 for v in part1]
        else:
            part2 = [float("nan")] * len(part1)
        current_row[middle + start: middle + stop] = part2


def any_alive(worker_list: list[Process]) -> bool:
    status_list = map(lambda x: x.is_alive(), worker_list)
    return any(status_list)


def main(image_dir: str | Path,
         depths: list[str],
         csv_path: str | Path,
         regex: str,
         config_path: str | Path,
         proc: int,
         ) -> None:
    # TODO: if the csv file already exists, check for coherence between
    #       number of colors, depths and dimensions of the csv file
    config_path = Path(config_path)
    config: ColorAndParams = get_color_and_params(config_path)
    colors = config["color_data"]["names"]

    sub_dirs = sorted_sub_dirs(image_dir)
    csv_file = fetch_csv(csv_path, depths, colors, sub_dirs)
    images = unprocessed_images(sub_dirs, csv_file, depths, colors, regex)
    remaining = len(images)
    print(f"{remaining} à traiter")

    in_queue, out_queue = Queue(), Queue()
    for img in images:
        in_queue.put(img)

    workers = init_workers(proc, config, in_queue, out_queue)
    for worker in workers:
        in_queue.put("STOP")
        worker.start()
        time.sleep(2.5)
        # Spread them in time to not use as much memory bandwidth
    table = read_csv(csv_file)
    while any_alive(workers) or not out_queue.empty():
        if out_queue.empty():
            time.sleep(1)
            print(f"{remaining} images restantes."
                  " En attente de données.", end='\r')
        else:
            # put values in table
            print(f"{remaining} images restantes."
                  " Écriture en cours...  ", end='\r')
            data_points: DataElement = out_queue.get()
            fill_data_points(table, data_points, len(depths), len(colors))
            write_csv(csv_file, table)
            remaining -= 1
    in_queue.close()
    out_queue.close()


def edit_config_file(k: int, path: Path, from_image: Path):
    config: TOMLDocument = get_color_and_params(path)
    config_table: tomlItems.Array = config["color_data"]["table"]
    color_table: npT.NDArray
    palette:     npT.NDArray
    labeled_img: npT.NDArray
    if k == 1 and from_image is None:
        color_table = np.array(config_table, dtype=np.uint8)
        palette = color_table[:, 0:3]
        img = cv.imread(config["reference_image"])
        labeled_img = label_img_fastest(img, color_table)
    else:
        if k == 1:
            k = len(config_table)
        echo("calcul des K moyennes, cela peut prendre du temps")
        img = cv.imread(from_image)
        palette, _, labeled_img = get_k_means(img, k)
        palette = palette.astype(np.uint8)
        labeled_img = labeled_img.reshape(img.shape[0:2]).astype(np.uint8)
    # Run the GUI - get the category for each shade
    echo("running gui")
    categories = run_gui(labeled_img, palette)
    # Save the results to config file
    category_count = count_categories(categories)
    categories = np.array(categories)[:, None]
    color_table = list(np.concatenate((palette, categories), axis=1))
    new_array = tomlkit.array()
    new_array.multiline(True)
    for row in color_table:
        new_array.add_line(list(map(int, list(row))))
    config["color_data"]["table"] = new_array
    if from_image is not None:
        # There are a lot of changes to take into account
        config["reference_image"] = from_image
        param_list:     tomlItems.AoT = config["det_params"]
        new_param_list: tomlItems.AoT
        param_count = len(param_list)
        if param_count > category_count:
            new_param_list = param_list[:category_count]
        elif param_count < category_count:
            new_param_list = param_list
            missing_params = range(param_count, category_count)
            color_names = map("color_{}".format, missing_params)
            config["color_data"]["names"].extend(color_names)
            missing_params = map(default_det_params, missing_params)
            new_param_list.extend(missing_params)
        else:
            new_param_list = param_list
        config["det_params"] = new_param_list
    TOMLFile(path).write(config)
