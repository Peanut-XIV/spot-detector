from spot_detector.model.project import Project
import sys
from pathlib import Path


def main(conf: Path):
    new_path = conf.parent / ("uint8_" + conf.name)
    if new_path.exists():
        print(f"{str(new_path)} existe déjà, au revoir")
        sys.exit(0)

    config = Project.from_path(str(conf))
    colors = config.configuration.shades
    for col in colors:
        col.r = col.r >> 8
        col.g = col.g >> 8
        col.b = col.b >> 8

    content = config.model_dump_json()
    with open(new_path, "+w") as f:
        f.write(content)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("1 seul argument svp")
        print("arg doit être un chemin et doit exister svp")
        print("le chemin doit être un fichier svp")
        sys.exit(0)
    conf = Path(sys.argv[1])

    if not conf.exists():
        print("arg doit être un chemin et doit exister svp")
        print("le chemin doit être un fichier svp")
        sys.exit(0)

    if not conf.is_file():
        print("le chemin doit être un fichier svp")
        sys.exit(0)

    main(conf)
