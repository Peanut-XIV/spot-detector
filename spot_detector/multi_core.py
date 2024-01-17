# Python standard library
from time import sleep
from multiprocessing import Queue, Process, parent_process
from typing import Union
# Project files
from spot_detector.process_chains import (
        count_spots_fourth_method, load_params)
from spot_detector.config import ColorAndParams, DetParams
from spot_detector.types import DataElement, ImageElement
# Other dependancies
import cv2 as cv
import numpy as np


def init_workers(count: int,
                 color_and_params: ColorAndParams,
                 in_queue: Queue,
                 out_queue: Queue,
                 ) -> list[Process]:
    """
    Créée un ensemble d'objets `multiprocessing.Process` mais n'invoque pas
    leur méthode `.start()`.
          `count`: Le nombre de Process à créer.
    `color_table`: La table contenant les informations nécessaire pour
                 simplifier les images. C'est une liste de liste
                 d'entiers et pas un array numpy car la table doit
                 être pickleable.
       `in_queue`: L'objet qui apporte les ImageElements aux processus.
      `out_queue`: L'objet qui réccupère les données produites par les
                 processus.
         `return`: La liste des Process.
    """
    # TODO create detectors from
    workers_list = []
    for i in range(count):
        worker = Process(
            target=img_processer,
            args=(in_queue, out_queue, color_and_params)
        )
        workers_list.append(worker)
    return workers_list


def img_processer(in_queue: Queue,
                  out_queue: Queue,
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
    parent = parent_process()
    while parent.is_alive():
        if in_queue.empty():
            sleep(1)
        else:
            job: Union[str, ImageElement] = in_queue.get()
            if job == "STOP":
                break
            folder_row, depth_col, path = job
            img = cv.imread(path)
            values = count_spots_fourth_method(img,
                                               color_table,
                                               color_and_params["det_params"])
            result: DataElement = (folder_row, depth_col, values)
            out_queue.put(result)


def init_detectors(detection_params: DetParams,
                   shades_count: int,
                   ) -> list[cv.SimpleBlobDetector]:
    """
    Broken, do not use!
    """
    detectors = []
    for setting in detection_params:
        params = load_params(setting, shades_count)
        detectors.append(cv.SimpleBlobDetector(params))
    return detectors
