# Python standard library
from pathlib import Path
# Project files
from spot_detector.config import get_cli_defaults, CLIDefaults
from spot_detector.file_utils import check_img_count
from spot_detector.main import main
# Other dependancies
import click
from pydantic import ValidationError
from click import BadParameter, group, argument, option, echo, confirm, STRING


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
    type=click.Path(file_okay=False,
                    dir_okay=True,
                    resolve_path=True,
                    path_type=Path),
    default=str(Path.home().joinpath(".spot-detector/")),
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


if __name__ == "__main__":
    cli()
