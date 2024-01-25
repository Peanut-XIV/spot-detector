from typing import Optional
from pathlib import Path


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
