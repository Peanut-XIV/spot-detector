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

