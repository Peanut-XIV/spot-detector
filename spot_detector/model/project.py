from pathlib import Path
import json
from typing import Self, Any, Optional

from numpy.typing import NDArray
from pydantic import BaseModel, field_validator, Field, ValidationError

from spot_detector.model.defaults import PROJECTS_LIST, get_recent_project_paths
from spot_detector.model.models import ColorAndParams, Shade
from spot_detector.model.reference_image import ReferenceImageModel
# from spot_detector.file_utils import VALID_IMAGE_MIME_TYPES
# import mimetypes


class PathError(BaseException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


# TODO: Add a post-init method to generate the image cache from the config, if
# the reference image is already provided
class Project(BaseModel):
    name: str = Field(max_length=40)  #  Validated for printable characters
    latest_save_path: Optional[str] = Field(default=None)
    reference_image_model: Optional[ReferenceImageModel] = Field(default=None)
    dust_filter_image_path: Optional[str] = Field(default=None)
    image_directory_path: Optional[str] = Field(default=None)
    configuration: ColorAndParams = Field(default_factory=ColorAndParams.from_defaults)

    @field_validator(
        "name",
        "latest_save_path",
        "dust_filter_image_path",
        "image_directory_path",
    )
    @classmethod
    def is_printable(cls, string: str | None):
        if string is not None and not string.isprintable():
            error = ValidationError()
            error.add_note(
                "A field within the config file contains non printable characters,"
                " it is therefore invalid"
            )
            raise error
        return string

    @classmethod
    def from_path(cls, project_file: str | Path) -> Self:
        with open(project_file, mode="r", encoding="UTF-8") as file:
            json_dict = json.load(file)
            content = cls(**json_dict)
        return content

    @classmethod
    def from_dict(cls, project_data: dict[str, Any]) -> Self:
        return cls(**project_data)

    def set_reference_image_path(self, image_path: Path | str):
        if isinstance(image_path, Path):
            self.reference_image_model = ReferenceImageModel(path=str(image_path))
        else:
            self.reference_image_model = ReferenceImageModel(path=image_path)

    def set_dust_filter(self, image_path: Path | str):
        if isinstance(image_path, Path):
            self.dust_filter_image_path = str(image_path)
        else:
            self.dust_filter_image_path = image_path

    def set_shades(self, lut: NDArray):
        """
        lut -> numpy array of shape (3, X) of integers
        """
        color_data = [Shade.from_pix(tuple(row)) for row in lut]
        self.configuration.shades = color_data

    def set_configuration(self, configuration: ColorAndParams):
        """
        Sets the configuration (the detection settings) of the project

        Takes the config given as parameter makes a deep copy and sets it as
        the detection settings configuration of this project object.

        Parameters
        ----------
        configuration: ColorAndParams
        """
        config_copy = configuration.model_copy(deep=True)
        self.configuration = config_copy

    def save_as(self, path: str | Path):
        old_path = self.latest_save_path
        self.latest_save_path = str(path)
        try:
            with open(path, "w", encoding="UTF-8") as file:
                json.dump(self.model_dump(), file)
        except OSError as e:
            self.latest_save_path = old_path
            raise e

        # add path to existing projects
        if str(path) not in get_recent_project_paths():
            with open(PROJECTS_LIST, "a", encoding="UTF-8") as file:
                file.write(str(path) + "\n")
