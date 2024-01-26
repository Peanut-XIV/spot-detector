from typing import Optional
from pathlib import Path
from numpy.typing import NDArray
import cv2 as cv


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


def fit_elements(elements: list[str]) -> list[str]:
    output = []
    line = ""
    for element in elements:
        if len(line) + len(element) > 80:
            output.append(line)
            line = ""
        line += element
        line += (20 - (len(line) % 20)) * " "
    output.append(line)
    return output


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
