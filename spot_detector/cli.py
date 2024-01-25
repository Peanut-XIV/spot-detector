# Python standard library
from pathlib import Path
from os import mkdir
# Project files
from spot_detector.config import (get_cli_defaults, get_color_and_params,
                                  CLIDefaults, create_new_config,
                                  )
from spot_detector.file_utils import check_img_count
from spot_detector.main import main, edit_config_file
# Other dependancies
import click
from tomlkit import TOMLDocument
from tomlkit.toml_file import TOMLFile
from pydantic import ValidationError
from click import (BadParameter, FileError, group, argument,
                   option, echo, confirm, STRING,
                   )


def confirm_new_cfg_file(path):
    if path.exists():
        if not path.is_file():
            raise FileError("Le chemin ne désigne pas un fichier.")
        confirm("Ce fichier existe déjà. "
                "Souhaitez-vous écrire par dessus ?",
                abort=True)
    else:
        if not path.parent.exists():
            confirm("Ce chemin n'existe pas encore. "
                    "Créer les dossiers manquants ?",
                    abort=True)
            mkdir(path.parent)


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


def get_defaults_or_error(defaults_file: str | Path) -> CLIDefaults:
    try:
        defaults = get_cli_defaults(defaults_file)
    except ValidationError as e:
        e2 = BadParameter("Le fichier de valeurs par"
                          " défaut n'est pas valide",
                          param_hint=["-d"])
        raise e2 from e
    return defaults


@group
def cli():
    pass


@cli.command
@argument(
    "dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@argument(
    "config",
    type=click.Path(file_okay=True,
                    dir_okay=True,
                    resolve_path=True,
                    path_type=Path),
    default=str(Path.home().joinpath(".spot-detector/config.toml")),
)
@option(
    "-n", "--sans-defaut", "--no-default", "no_default",
    is_flag=True, flag_value=True, default=False,
    help="Permet d'empêcher d'utiliser les valeurs par défaut lors du"
         "fonctionnement du programme."
)
@option(
    "-d", "--vals-par-defaut", "--defaults", "defaults_file",
    type=click.Path(exists=True,
                    file_okay=True,
                    dir_okay=False,
                    resolve_path=True,
                    path_type=Path),
    default=str(Path.home().joinpath(".spot-detector/defaults.toml")),
    help="Le chemin du dossier de configuration du programme."
)
@option(
    "-p", "--profondeurs", "depths", type=STRING, default=None,
    help="Les valeurs de profondeur présentes dans le nom des images, "
         "séprarées par des espaces le tout entre deux guillemets. "
         "Exemple : `spot-detector ./chemin/dossier -d=\"1 2 3 4 5\"`",
)
@option(
    "-r", "--regex", type=STRING, default=None,
    help="L'expression régulière qui décrit le nom des images à traiter. "
         "Doit être écrite entre deux apostrophes. Utilisez $value pour "
         "insérer la valeur de profondeur correspondante. "
         "Exemple : `-r='image$value\\d\\.(jpeg|png)'`",
)
@option(
    "-f", "--fichier-destination", "csv_path",
    type=click.Path(file_okay=True, dir_okay=False), default=None,
    help="La localisation du fichier csv de résultat.",
)
@option(
    "-j", "--nbr-proc", "--proc-count", "proc",
    type=click.INT, default=1,
    help="le nombre de processus qui traitent les images. Un processus par "
         "cœur de CPU ou moins pour des performances optimales. Peut être "
         "limité par la mémoire vive.",
)
@option("-y", is_flag=True, flag_value=True, default=False)
def spot_detector(dir: str,
                  config: str,
                  no_default: bool,
                  defaults_file: str,
                  depths: list[str],
                  regex: str,
                  csv_path: str,
                  y: bool,
                  proc: int,
                  ) -> None:
    if not no_default:
        defaults = get_defaults_or_error(defaults_file)
        dir = dir or defaults["image_dir"]
        csv_path = csv_path or defaults["csv_path"]
        regex = regex or defaults["regex"]
        depths = depths or defaults["depths"]

    csv = Path(csv_path)
    if csv.exists() and not y:
        confirm(f"{csv.name} existe déjà. Traiter les images manquantes ?",
                abort=True)

    sdirs = list(filter(lambda x: x.is_dir(), Path(dir).iterdir()))
    mismatches, counts = check_img_count(len(depths), sdirs)
    if mismatches and not y:
        bad_dirs = filter(lambda p: p[1] != len(depths), zip(sdirs, counts))
        dir_and_count = map(lambda p: f"{p[0].name}: {p[1]}", bad_dirs)
        lines = fit_elements(dir_and_count)
        if mismatches > 1:
            echo(f"{mismatches} dossiers ont un nombre d'images "
                 f"inattendu. (attendait {len(depths)} images) :\n"
                 "FICHIER: NOMBRE D'IMAGES")
            for line in lines:
                echo(line)
        else:
            d_name, i_num = list(bad_dirs)[0]
            echo(f"Le dossier {d_name} contient {i_num} images alors"
                 f" que {len(depths)} étaient attendues.")
        confirm("Continuer ?", abort=True)

    main(dir, depths, csv_path, regex, config, proc)


@cli.command
@argument(
    "path", type=click.Path(file_okay=True, dir_okay=False),
)
@option(
    "-c", "--create", "--creer", is_flag=True, default=False,
    help="Créée un ficher de configuration au chemin indiqué."
)
@option(
    "-e", "--edit", "--editer",
    is_flag=False, flag_value=1, default=0, type=click.INT,
    help="Modifie la palette contenue dans le fichier indiqué. "
         "Indiquer une valeur après l'option permet de changer le nombre de "
         "nuances dans la palette. Une valeur de 1 reviens à ne pas indiquer "
         "de valeur, et réutilise le nombre de nuances de l'ancienne palette. "
         "Cette option est compatible avec l'option `-i`. Utiliser cette "
         "option avec un fichier nouvellement créé nécessite l'option `-i`.",
)
@option(
    "-i", "--from-image", "--depuis-image",
    type=click.Path(),
    help="Indique le chemin de l'image de référence de la palette. "
         "Ne fonctionne que si l'option `-e` est activée.",
)
@option(
    "-d", "--duplicate", "--dupliquer",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Duplique le fichier du premier chemin indiqué vers le second. Si "
         "cette option est utilisée avec l'option `e`, alors seul le "
         "fichier de destination sera modifié. Cette option n'est pas "
         "compatible avec l'option `-c`.",
)
def palette_editor(path,
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
                    "Le fichier de destination n'est pas un fichier .toml.")
    if from_image is not None and not edit:
        raise BadParameter("`-i` utilisé sans `-e`.")
    if duplicate and create:
        raise BadParameter("`-c utilisé avec `-d`.")
    if path.suffix != '.toml':
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


if __name__ == "__main__":
    cli()
