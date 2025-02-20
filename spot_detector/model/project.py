from pathlib import Path
import json
from typing import Self, Any, Optional

from numpy.typing import NDArray
from pydantic import BaseModel, field_validator, Field, ValidationError

from spot_detector.model.models import ColorAndParams, ColorData, DetParams
# from spot_detector.file_utils import VALID_IMAGE_MIME_TYPES
# import mimetypes


class PathError(BaseException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class Project(BaseModel):
    name: str = Field(max_length=40)  #  Validated for printable characters
    latest_save_path: Optional[str] = Field(default=None)
    ref_image_path: Optional[str] = Field(default=None)
    dust_filter_image_path: Optional[str] = Field(default=None)
    image_directory_path: Optional[str] = Field(default=None)
    configuration: Optional[ColorAndParams] = Field(default=None)

    @field_validator(
        "name",
        "latest_save_path",
        "ref_image_path",
        "dust_filter_image_path",
        "image_directory_path",
    )
    def is_printable(cls, string: str | None):
        if string is not None and not string.isprintable():
            error = ValidationError()
            error.add_note(
                "A field within the config file contains non printable characters,"
                " it is therfore invalid"
            )
            raise error

    @classmethod
    def from_path(cls, project_file: str) -> Self:
        with open(project_file, mode="r", encoding="UTF-8") as file:
            json_dict = json.load(file)
            content = cls(**json_dict)
        return content

    @classmethod
    def from_dict(cls, project_data: dict[str, Any]) -> Self:
        return cls(**project_data)

    def set_ref_image_path(self, image_path: Path | str):
        if isinstance(image_path, Path):
            self.ref_image_path = str(image_path)
        else:
            self.ref_image_path = image_path

    def set_ref_dust_filter(self, image_path: Path | str):
        if isinstance(image_path, Path):
            self.dust_filter_image_path = str(image_path)
        else:
            self.dust_filter_image_path = image_path

    def set_lut(self, lut: NDArray):
        color_data = ColorData.from_lut(lut)
        if self.configuration is None:
            # make new config
            assert self.ref_image_path is not None
            ref_image = self.ref_image_path
            det_params = []
            self.configuration = ColorAndParams(
                reference_image=ref_image,
                color_data=color_data,
                det_params=det_params,
            )
        else:
            self.configuration.color_data = color_data
