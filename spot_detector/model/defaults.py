import json
from pathlib import Path
from typing import Self


class AppDefaults:
    def __init__(self, values) -> None:
        self.values = values

    @classmethod
    def from_file(cls, path: Path) -> Self:
        with open(path, mode="r", encoding="UTF-8") as config_file:
            defaults = cls(json.load(config_file))
        return defaults


PROJECTS_LIST = Path.home().joinpath(".spot_detector/recent_projects.txt")


def is_valid_project_path(path: str) -> bool:
    path_obj = Path(path)
    output = (
        (not path.startswith("#"))  # ignore comments
        and path_obj.exists()
        and path_obj.is_file()
        and path_obj.suffix == ".spot"  # Actually a json file but *hush*
    )
    return output


def get_recent_project_paths() -> list[str]:
    with open(PROJECTS_LIST, "r", encoding="UTF-8") as file:
        projects = [line for line in file if is_valid_project_path(line)]
    return projects
