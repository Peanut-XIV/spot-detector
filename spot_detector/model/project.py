from enum import Enum
from pathlib import Path
import json
from typing_extensions import Self

from pydantic import BaseModel, field_validator, Field, ValidationError


class PathError(BaseException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class Project(BaseModel):
    name: str = Field(max_length=40)
    ref_image_path: str
    dust_filter_path: str
    image_directory_path: str

    @field_validator(
        "name", "ref_image_path", "dust_filter_path", "image_directory_path"
    )
    def is_printable(cls, string: str):
        if not string.isprintable():
            error = ValidationError()
            error.add_note(
                "expected fields 'ref_image_path', 'dust_filter_path'"
                " and 'image_directory_path' to only contain printable characters."
                "At least one of them contain a non-printable character"
            )
            raise error

    @classmethod
    def from_path(cls, project_file: str) -> Self:
        with open(project_file, mode="r", encoding="UTF-8") as file:
            json_dict = json.load(file)
            content = cls(**json_dict)
        return content

    def is_valid_image_format(self, path: Path):
        valid_extensions = [
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".tiff",
        ]
        if path.suffix not in valid_extensions:
            return False
        else:
            return True

    def validate_image_path(self, path: Path | str, is_dir: bool = False):
        path_obj = Path(path)
        error = None
        if not path_obj.exists():
            error = PathError()
            error.add_note(f"Expected Path {str(Path)} to exist")
        elif not path_obj.is_file():
            error = PathError()
            error.add_note(f"Expected Path {str(Path)} to be a file")
        elif not (is_dir or self.is_valid_image_format(path_obj)):
            error = PathError()
            error.add_note(
                f"Expected file {str(Path)} to be an image of format"
                "'.png', '.jpg', '.jpeg', '.webp' or '.tiff'"
            )
        if error is not None:
            raise error

    def set_dust_filter_path(self, path: Path | str, validate: bool = True):
        if validate:
            try:
                self.validate_image_path(path)
            except PathError as e:
                e.add_note(
                    f"Could not set {str(path)} as dust_filter_path attribute "
                    f"of project {self.name}"
                )
                raise e
        self.dust_filter_path = str(path)

    def set_ref_image_path(self, path: Path | str, validate: bool = True):
        if validate:
            try:
                self.validate_image_path(path)
            except PathError as e:
                e.add_note(
                    f"Could not set {str(path)} as ref_image_path attribute "
                    f"of project {self.name}"
                )
                raise e
        self.ref_image_path = str(path)

    def set_image_directory_path(self, path: Path | str, validate: bool = True):
        if validate:
            try:
                self.validate_image_path(path, True)
            except PathError as e:
                e.add_note(
                    f"Could not set {str(path)} as image_directory_path "
                    f"attribute of project {self.name}"
                )
                raise e
        self.ref_image_path = str(path)

    def check_fields(self) -> dict | None:
        # Check field 1
        # Check field 2
        # Check field 3
        return None
