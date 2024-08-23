# Python standard library
from pathlib import Path

# Other dependancies
import click
from click import (BadParameter, FileError, argument, command, confirm, echo,
                   option)
from tomlkit import TOMLDocument
from tomlkit.toml_file import TOMLFile

# Project files
from .config import (create_new_config, get_color_and_params,
                     get_defaults_or_error)
from .core import detect, edit_config_file
from .file_utils import check_img_count, confirm_new_cfg_file
from .misc import fit_elements


@command()
@argument(
    "config",
    type=click.Path(
        file_okay=True, dir_okay=True, resolve_path=True, path_type=Path
    ),
)
@argument(
    "dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=None
)
@argument(
    "depths",
    type=click.STRING,
    # help="Les valeurs de profondeur présentes dans le nom des images, "
    # "séprarées par des espaces le tout entre deux guillemets. "
    # 'Exemple : `spot-detector ./chemin/dossier -d "1 2 3 4 5"`',
)
@argument(
    "regex",
    type=click.STRING,
    # help="L'expression régulière qui décrit le nom des images à traiter. "
    #      "Doit être écrite entre deux apostrophes. Utilisez $value pour "
    #      "insérer la valeur de profondeur correspondante. "
    #      "Exemple : `-r 'image$value\\d\\.(jpeg|png)'`",
)
@option(
    "-f",
    "--fichier-destination",
    "csv_path",
    type=click.Path(file_okay=True, dir_okay=False),
    default=None,
    help="La localisation du fichier csv de résultat.",
)
@option(
    "-j",
    "--nbr-proc",
    "--proc-count",
    "proc",
    type=click.INT,
    default=1,
    help="le nombre de processus qui traitent les images. Un processus par "
    "cœur de CPU ou moins pour des performances optimales. Peut être "
    "limité par la mémoire vive.",
)
@option("-y", is_flag=True, flag_value=True, default=False)
def detector(
    dir: str | Path | None,
    config: str | Path,
    depths: str,
    regex: str,
    csv_path: str | None,
    y: bool,
    proc: int,
) -> None:

    if dir is None:
        dir = Path.cwd()
    else:
        dir = Path(dir)
    depths_list = depths.split(" ")
    if csv_path is None:
        csv = dir.joinpath("results.csv")
    else:
        csv = Path(csv_path)
    if csv.exists() and not y:
        confirm(
            f"{csv.name} existe déjà. Traiter les images manquantes ?",
            abort=True,
        )
    img_directories = list(filter(lambda x: x.is_dir(), dir.iterdir()))
    mismatches, counts = check_img_count(len(depths_list), img_directories)
    if mismatches and not y:
        bad_dirs = filter(lambda p: p[1] != len(depths_list), zip(img_directories, counts))
        dir_and_count = list(map(lambda p: f"{p[0].name}: {p[1]}", bad_dirs))
        lines = fit_elements(dir_and_count)
        if mismatches > 1:
            echo(
                f"{mismatches} dossiers ont un nombre d'images "
                f"inattendu. (attendait {len(depths_list)} images) :\n"
                "FICHIER: NOMBRE D'IMAGES"
            )
            for line in lines:
                echo(line)
        else:
            d_name, i_num = list(bad_dirs)[0]
            echo(
                f"Le dossier {d_name} contient {i_num} images alors"
                f" que {len(depths_list)} étaient attendues."
            )
        confirm("Continuer ?", abort=True)

    detect(dir, depths_list, csv, regex, config, proc)


@command()
@argument(
    "path",
    type=click.Path(file_okay=True, dir_okay=False),
)
@option(
    "-c",
    "--create",
    "--creer",
    is_flag=True,
    default=False,
    help="Créée un ficher de configuration au chemin indiqué.",
)
@option(
    "-e",
    "--edit",
    "--editer",
    is_flag=False,
    flag_value=1,
    default=0,
    type=click.INT,
    help="Modifie la palette contenue dans le fichier indiqué. "
    "Indiquer une valeur après l'option permet de changer le nombre de "
    "nuances dans la palette. Une valeur de 1 reviens à ne pas indiquer "
    "de valeur, et réutilise le nombre de nuances de l'ancienne palette. "
    "Cette option est compatible avec l'option `-i`. Utiliser cette "
    "option avec un fichier nouvellement créé nécessite l'option `-i`.",
)
@option(
    "-i",
    "--from-image",
    "--depuis-image",
    type=click.Path(),
    help="Indique le chemin de l'image de référence de la palette. "
    "Ne fonctionne que si l'option `-e` est activée.",
)
@option(
    "-d",
    "--duplicate",
    "--dupliquer",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Duplique le fichier du premier chemin indiqué vers le second. Si "
    "cette option est utilisée avec l'option `e`, alors seul le "
    "fichier de destination sera modifié. Cette option n'est pas "
    "compatible avec l'option `-c`.",
)
def palette_editor(
    path,
    create,
    edit,
    from_image,
    duplicate,
):
    # Abort in case of misuse
    path = Path(path)
    if duplicate is not None:
        duplicate = Path(duplicate)
        if not path.exists():
            raise FileNotFoundError("Le fichier source n'existe pas")
        if duplicate.suffix != ".toml":
            raise FileError(
                "Le fichier de destination n'est pas un fichier .toml."
            )
    if from_image is not None and not edit:
        raise BadParameter("`-i` utilisé sans `-e`.")
    if duplicate and create:
        raise BadParameter("`-c utilisé avec `-d`.")
    if path.suffix != ".toml":
        raise FileError("Le fichier source n'est pas un fichier .toml.")
    # HAPPY PATH
    if create:
        # aborts if user doesn't want to overwrite
        confirm_new_cfg_file(path)
        config: TOMLDocument = create_new_config()
        TOMLFile(path).write(config)
    elif duplicate:
        # aborts if user doesn't want to overwrite
        confirm_new_cfg_file(duplicate)
        config: TOMLDocument = get_color_and_params(path)
        TOMLFile(duplicate).write(config)
        path = duplicate
    if edit:
        edit_config_file(edit, path, from_image)
