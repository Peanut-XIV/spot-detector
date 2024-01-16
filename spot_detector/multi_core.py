# Python standard library
from typing import TypeAlias
import multiprocessing as mp
# Project files
from spot_detector.process_chains import count_spots_third_method, count_spots_fourth_method, load_params
from spot_detector.config import ColorAndParams, DetParams
# Other dependancies
import cv2 as cv
import numpy as np

ImageElement: TypeAlias = tuple[int, int, str]


def init_workers(count: int,
                 color_and_params: ColorAndParams,
                 ) -> list[mp.Process, mp.Queue, mp.Queue]:
    """
    Créée un ensemble d'objets `multiprocessing.Process` mais n'invoque pas
    leur méthode `.start()`.

          `count`: Le nombre de Process à créer.
    `color_table`: La table contenant les informations nécessaire pour
                 simplifier les images. C'est une liste de liste
                 d'entiers et pas un array numpy car la table doit
                 être pickleable.
         `return`: La liste des Process.
    """
    mp.set_start_method("spawn")
    in_queue = mp.Queue()
    out_queue = mp.Queue()
    # TODO create detectors from
    workers_list = []
    for i in range(count):
        worker = mp.Process(
            target=img_processer,
            args=(in_queue, out_queue, color_and_params)
        )
        workers_list.append(worker)
    return workers_list, in_queue, out_queue


def img_processer(in_queue: mp.Queue,
                  out_queue: mp.Queue,
                  color_and_params: ColorAndParams,
                  ) -> None:
    """
    La fonction qui attend les instructions et traites les `ImageElements` qui
    lui sont transmis par la `in_queue` et renvoie le résultat par la
    `out_queue`.

       `in_queue`: L'objet `multiprocessing.Queue` depuis lequel arrive les
                 les `ImageElements`.
      `out_queue`: L'objet `multiprocessing.Queue` dans lequel les valeurs
                 calculées sont retournées.
    `color_table`: La table contenant les informations nécessaires pour
                 simplifier les images. C'est une liste de listes d'entiers
                 et pas un array Numpy car la table doit être pickleable.
         `return`: Rien.
    """
    color_table = np.array(color_and_params["color_data"]["table"])
    # detectors = init_detectors(color_and_params["det_params"],
    #                            len(color_table))
    for job in iter(in_queue.get, 'STOP'):
        folder_row, depth_col, path = job
        img = cv.imread(path)
        values = count_spots_fourth_method(img, color_table, color_and_params["det_params"])
        out_queue.put((folder_row, depth_col, values))


def init_detectors(detection_params: DetParams,
                   shades_count: int,
                   ) -> list[cv.SimpleBlobDetector]:
    detectors = []
    for setting in detection_params:
        params = load_params(setting, shades_count)
        detectors.append(cv.SimpleBlobDetector(params))
    return detectors
