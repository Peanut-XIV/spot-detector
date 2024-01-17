# Python standard library
from multiprocessing import Queue, Process
from pathlib import Path
from typing import Optional
import csv
import time
# Project files
from spot_detector.file_utils import match_dir_items
from spot_detector.multi_core import init_workers
from spot_detector.config import get_color_and_params, ColorAndParams
from spot_detector.types import (
        DataRow,
        DataTable,
        ImageElement,
        DataElement,
)


def read_csv(csv_file: str | Path) -> DataTable:
    """
    Lit le fichier csv `csv_file` et retourne son contenu, à partir de la 3ème
    ligne, dans une liste de liste.
    `csv_file`: Objet de chemin du fichier csv.
      `return`: la table, qui est une liste de liste de chaines de caractères.
    """
    table = []
    with open(Path(csv_file), "r", newline='') as file:
        reader = csv.reader(file, dialect='unix')
        for line in reader:
            table.append(line)
    return table


def write_csv(csv_file: str | Path,
              table: DataTable,
              ) -> None:
    """
    Enregistre les valeurs du tableau `table` dans le fichier csv donné.
    `csv_file`: L'objet de chemin du fichier en question.
       `table`: La liste de listes de chaines de caractères qui seront
              enregistrées dans le fichier csv.
      `return`: Rien.
    """
    with open(Path(csv_file), 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(table)


def first_two_rows(depths: list[str],
                   colors: list[str],
                   ) -> tuple[DataRow, DataRow]:
    """
    Créée les deux premières ligne du document csv.
    La première indique la catégorie de donnée (couleur, total - nbr, %tage).
    La seconde indique la valeur de profondeur associée à chaque colonne.
    `depths`: Liste des valeurs de profondeur.
    `colors`: Liste des noms de couleurs.
    `return`: Les deux lignes sous forme de listes de chaines de caractères.
    """
    empty_list = [""] * (len(depths) - 1)
    label_row_1 = [""]
    for color in colors:
        label_row_1 += [f"Nbr {color}"] + empty_list
    label_row_1 += ["Nbr all colors"] + empty_list
    for color in colors:
        label_row_1 += [f"%tage {color}"] + empty_list
    label_row_1 += ["%tage all colors"] + empty_list
    label_row_2 = ["sub_directory\\depth"] + 2 * (1 + len(colors)) * depths
    return label_row_1, label_row_2


def is_valid_csv(file: str | Path,
                 expected_rows: int,
                 expected_cols: int,
                 ) -> bool:
    contents = []
    with open(file, "r", newline="") as io_stream:
        reader = csv.reader(io_stream)
        contents = [line for line in reader]
    if len(contents) != expected_rows + 2:
        return False
    col_count = map(len, contents)
    mismatches = filter(lambda c: c != expected_cols, col_count)
    if len(list(mismatches)):
        return False
    return True


def fetch_csv(csv_path: str | Path,
              depths: list[str],
              colors: list[str],
              sub_directories: list[Path],
              ) -> Path:
    """
    Retourne l'objet de chemin du fichier `csv_path` s'il existe. Sinon, la
    fonction en créée un nouveau correspondant aux différentes valeurs
    indiquées : couleurs => `colors`
                dossiers => `sub_directories`
             profondeurs => `depths`
    l'enregistre dans le système de fichiers et retourne son objet de chemin.
           `csv_path`: La chaine de charactères correspondant au chemin du csv.
             `depths`: Les différentes profondeurs traitées par le tableau csv.
             `colors`: Les différentes couleurs traitées par le tableau csv.
    `sub_directories`: Les dossiers dont les images seront traitées et leur
                     valeurs inscrites dans le tableau csv.
             `return`: L'objet de chemin du fichier csv.
    """
    path_obj = Path(csv_path)
    col_count = 1 + (1 + len(colors)) * len(depths) * 2
    if path_obj.is_file():
        if is_valid_csv(path_obj, len(sub_directories), col_count):
            return path_obj
        else:
            raise FileExistsError(
                f"Les dimensions du fichier {path_obj.name} "
                "ne correspondent pas aux paramètres fournis"
            )
    # otherwise, create a new csv file
    label_row_1, label_row_2 = first_two_rows(depths, colors)
    empty_part = [""] * (col_count - 1)
    rows = []
    for sub_dir in sub_directories:
        if sub_dir.is_dir() and sub_dir.name[0] != '.':
            rows.append([sub_dir.name] + empty_part)
    with open(path_obj, "x+", newline='') as csv_file:
        writer = csv.writer(csv_file, dialect='unix')
        writer.writerows((label_row_1, label_row_2))
        writer.writerows(rows)
    return path_obj


def map_folder_to_row(table: DataTable) -> dict[str, int]:
    """
    Retourne un dictionnaire qui associe, pour chaque valeur de la première
    colonne de `table`, son numéro de ligne associé.
    Le comptage des lignes commence à partir de 0 mais les deux premières
    lignes sont exclues car ce sont des étiquettes.
    Le plus petit numéro est donc 2.
     `table`: liste de listes de valeurs textuelles
    `return`: un dictionnaire aux entrées de la forme
            {"nom_dossier": num_ligne}
    """
    folder_name = [row[0] for row in table[2:]]
    row_number = range(2, len(table))
    f2r_dict = dict(zip(folder_name, row_number))
    return f2r_dict


def unprocessed_images(sub_directories: list[Path],
                       csv_file: str | Path,
                       depths: list[str],
                       colors: list[str],
                       regex: str,
                       ) -> list[ImageElement]:
    """
    Donne les images présentes dans les différents dossiers `sub_directories`
    qui n'ont pas été traitées et dont les valeurs ne sont pas indiquées dans
    le fichier `csv_file`.

    `sub_directories`: Les différents dossiers en question.
           `csv_file`: Le fichier où sont renseignées les valeurs
                     des images traitées.
             `depths`: Les différentes profondeurs traitées dans le csv.
             `colors`: Les différentes couleurs traitées dans le csv.
              `regex`: L'expression régulière qui permet d'identifier
                     précisément le nom d'un fichier d'image, avec la valeur
                     de profondeur remplacée par $value.
             `return`: Les images non-traitées, sous la forme d'une liste
                     d'ImageElement. C'est-à-dire, un tuple
                     (ligne, colonne, chemin).
    """
    table = read_csv(csv_file)
    unprocessed = []
    fname_2_row = map_folder_to_row(table)
    for sub_dir in sub_directories:
        row_nbr = fname_2_row[sub_dir.name]
        for depth_nbr, depth in enumerate(depths):
            matching_files = match_dir_items(sub_dir, regex, depth)
            if len(matching_files) > 1:
                print("Attention, plusieurs images correspondent à la même"
                      f"profondeur dans le dossier {sub_dir.name} :")
                print([file.name for file in matching_files])
            img: ImageElement = (row_nbr, depth_nbr, str(matching_files[0]))
            if is_img_processed(img, table, len(depths), len(colors)):
                continue
            else:
                unprocessed.append(img)
    return unprocessed


def is_img_processed(img: ImageElement,
                     table: DataTable,
                     depth_count: int,
                     color_count: int,
                     ) -> bool:
    """
    Indique si l'image `img` a déjà été traitée dans `table`.
    Nécessite le nombre de couleurs différentes `color_count`
    et de profondeurs différentes `depth_count`.

            `img`: L'élément d'image (ligne, colonne, chemin du fichier)
          `table`: la table en question: liste de listes
    `depth_count`: le nombre de profondeurs différentes traitées dans la table
    `color_count`: le nombre de couleurs différentes traitées dans la table
         `return`: la réponse à la question, sous forme d'un booléen
    """
    row_num, col_num, _ = img
    if col_num >= depth_count or col_num < 0:
        print(f"ERREUR, profondeur hors limites pour l'image {img}")
        return True  # pour ne pas traiter l'image incriminée
    row = table[row_num]
    start = 1 + col_num
    stop = color_count * depth_count
    step = depth_count
    val_unfilled = [val == '' for val in row[start: stop: step]]
    if any(val_unfilled):
        return False
    else:
        return True


def sorted_sub_dirs(path: str | Path) -> list[Path]:
    """
    Une fonction qui donne les sous-dossiers d'un dossier,
    triés par ordre alphabétique.

      `path`: un objet de chemin du dossier principal
    `return`: la liste triée des sous-dossiers qu'il contient
    """
    subs = [e for e in Path(path).iterdir() if e.is_dir()]
    return sorted(subs)


def ask_img_dir(default_value: Optional[str]) -> Path:
    chemin_dossier = input(
            "Chemin du dossier contenant les sous-dossiers d'image:\n"
            f"{default_value} par défaut\n"
    )
    if chemin_dossier == "":
        chemin_dossier = default_value
    return Path(chemin_dossier)


def ask_depths(default_value: Optional[list[str]]) -> list[str]:
    profondeurs = input(
        "Liste de valeurs de profondeur\n"
        f"{default_value} par défaut\n"
    )
    if profondeurs == "":
        profondeurs = default_value
    else:
        profondeurs = profondeurs.split(" ")
    return profondeurs


def ask_csv_path(default_value: Optional[str]) -> str:
    chemin_tableur = input(
        "Chemin du document csv :\n"
        f"{default_value} par défaut\n"
    )
    if chemin_tableur == "":
        chemin_tableur = default_value
    return chemin_tableur


def ask_regex(default_value: Optional[str]) -> str:
    motif = input(
        "Format du nom d'image en fonction de la profondeur:\n"
        f"{default_value} par défaut\n"
    )
    if motif == "":
        motif = default_value
    return motif


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
         config: str | Path,
         ) -> None:
    # TODO: if the csv file already exists, check for coherence between
    #       number of colors, depths and dimensions of the csv file
    cap_path = Path(config).joinpath("color_and_detection.toml")
    cap: ColorAndParams = get_color_and_params(cap_path)
    colors = cap["color_data"]["names"]

    sub_dirs = sorted_sub_dirs(image_dir)
    csv_file = fetch_csv(csv_path, depths, colors, sub_dirs)
    images = unprocessed_images(sub_dirs, csv_file, depths, colors, regex)
    remaining = len(images)
    print(f"{remaining} à traiter")

    in_queue, out_queue = Queue(), Queue()
    for img in images:
        in_queue.put(img)

    workers = init_workers(9, cap, in_queue, out_queue)
    for worker in workers:
        in_queue.put("STOP")
        worker.start()
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
