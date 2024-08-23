# Python standard library
from pathlib import Path

# Other dependancies
import click
from click import (
    BadParameter, FileError,
    argument, command, option
)
from tomlkit.toml_file import TOMLFile

# Project files
from spot_detector.config import (ColorAndParams, create_new_config, get_color_and_params)
from spot_detector.core import edit_config_file
from spot_detector.file_utils import confirm_new_cfg_file




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
        configuration: ColorAndParams = create_new_config()
        TOMLFile(path).write(configuration)
    elif duplicate:
        # aborts if user doesn't want to overwrite
        confirm_new_cfg_file(duplicate)
        configuration: ColorAndParams = get_color_and_params(path)
        TOMLFile(duplicate).write(configuration)
        path = duplicate
    if edit:
        edit_config_file(edit, path, from_image)
