# Python standard library
import csv
import re
import string
from os import mkdir
from pathlib import Path

# Other dependancies
import numpy as np
from click import FileError, confirm

# Project Files
from .types import DataRow, DataTable, ImageElement

im_ext = re.compile(r".+\.(jpe?g|JPE?G|png|PNG)")


def read_csv(csv_file: str | Path) -> DataTable:
    """
    Lit le fichier csv `csv_file` et retourne son contenu, à partir de la 3ème
    ligne, dans une liste de liste.
    `csv_file`: Objet de chemin du fichier csv.
      `return`: la table, qui est une liste de liste de chaines de caractères.
    """
    table = []
    with open(Path(csv_file), "r", newline="") as file:
        reader = csv.reader(file, dialect="unix")
        for line in reader:
            table.append(line)
    return table


def write_csv(
    csv_file: str | Path,
    table: DataTable,
) -> None:
    """
    Enregistre les valeurs du tableau `table` dans le fichier csv donné.
    `csv_file`: L'objet de chemin du fichier en question.
       `table`: La liste de listes de chaines de caractères qui seront
              enregistrées dans le fichier csv.
      `return`: Rien.
    """
    with open(Path(csv_file), "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(table)


def is_valid_csv(
    file: str | Path,
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


def fetch_csv(
    csv_path: str | Path,
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
        if sub_dir.is_dir() and sub_dir.name[0] != ".":
            rows.append([sub_dir.name] + empty_part)
    with open(path_obj, "x+", newline="") as csv_file:
        writer = csv.writer(csv_file, dialect="unix")
        writer.writerows((label_row_1, label_row_2))
        writer.writerows(rows)
    return path_obj


def first_two_rows(
    depths: list[str],
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


def unprocessed_images(
    sub_directories: list[Path],
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
                print(
                    "Attention, plusieurs images correspondent à la même"
                    f"profondeur dans le dossier {sub_dir.name} :"
                )
                print([file.name for file in matching_files])
            img: ImageElement = (row_nbr, depth_nbr, str(matching_files[0]))
            if is_img_processed(img, table, len(depths), len(colors)):
                continue
            else:
                unprocessed.append(img)
    return unprocessed


def is_img_processed(
    img: ImageElement,
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
    val_unfilled = [val == "" for val in row[start:stop:step]]
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


def incoherent_file(
    file_path: str | Path,
    should_exist: bool,
) -> bool:
    obj = Path(file_path)
    is_file = obj.exists() and obj.is_file()
    return is_file == should_exist


def is_im_file(obj: Path) -> bool:
    return bool(obj.is_file() and im_ext.match(obj.name))


def count_images(dir: Path) -> int:
    return sum(map(is_im_file, dir.iterdir()))


def check_img_count(
    expected: int,
    dossiers: list[Path],
) -> tuple[int, list[int]]:
    image_counts = list(map(count_images, dossiers))
    mismatches = len(list(filter(lambda n_im: n_im != expected, image_counts)))
    return mismatches, image_counts


# Not used
def get_color_table_array(path: str = "data_good.csv") -> np.ndarray:
    color_table = []
    with open(path, "r", newline="") as file:
        reader = csv.reader(file)
        for line in reader:
            color_table.append(line)
    # eliminate first row (labels) and last row if empty
    if color_table[-1] == [""] * len(color_table[0]):
        color_table = color_table[1:-1]
    else:
        color_table = color_table[1:]
    color_table = map(lambda L: list(map(int, L)), color_table)
    color_table = np.array(list(color_table))
    return color_table


# Obsolete
def get_unprocessed_directories(
    csv_path: str | Path,
    main_dir: str | Path,
) -> tuple[bool, list[Path]]:
    if not Path(csv_path).exists():
        dirs = [subd for subd in Path(main_dir).iterdir() if subd.is_dir()]
        return False, dirs
    processed_directories = []
    csv_exists = False
    if Path(csv_path).exists():
        csv_exists = True
        with open(csv_path, "r", newline="") as tableur:
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


def match_dir_items(
    dir: str | Path,
    pattern: str,
    inserted_value: str,
) -> list[Path]:
    pattern = string.Template(pattern)
    pattern = pattern.substitute(value=re.escape(inserted_value))
    regex = re.compile(pattern)
    dir = Path(dir)
    return list(filter(lambda x: regex.fullmatch(x.name), dir.iterdir()))


def confirm_new_cfg_file(path):
    if path.exists():
        if not path.is_file():
            raise FileError("Le chemin ne désigne pas un fichier.")
        confirm(
            "Ce fichier existe déjà. " "Souhaitez-vous écrire par dessus ?",
            abort=True,
        )
    else:
        if not path.parent.exists():
            confirm(
                "Ce chemin n'existe pas encore. "
                "Créer les dossiers manquants ?",
                abort=True,
            )
            mkdir(path.parent)
