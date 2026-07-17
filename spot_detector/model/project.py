from pathlib import Path
import json
from typing import Self, Any

from numpy import uint8, uint16
from numpy.typing import NDArray
from pydantic import BaseModel, field_validator, Field, ValidationError

from spot_detector.file_utils import add_to_recent_projects
from spot_detector.model.defaults import PROJECTS_LIST, get_recent_project_paths
from spot_detector.model.models import ColorAndParams, Shade
from spot_detector.model.processing_settings_models import ProcessingSettingsModel
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
    latest_save_path: str | None = Field(default=None)
    reference_image_model: ReferenceImageModel | None = Field(default=None)
    configuration: ColorAndParams = Field(default_factory=ColorAndParams.from_defaults)
    processing_settings: ProcessingSettingsModel | None = Field(default=None)

    @field_validator(
        "name",
        "latest_save_path",
    )
    @classmethod
    def is_printable(cls, string: str | None):
        if string is not None and not string.isprintable():
            msg = "A field within the config file contains non "\
                 +"printable characters, it is therefore invalid"
            error = ValidationError()
            error.add_note(msg)
            raise error
        return string

    @classmethod
    def from_path(cls, project_file: str | Path) -> Self:
        with open(project_file, mode="r", encoding="UTF-8") as file:
            content = cls(**(json.load(file)))  # pyright: ignore[reportAny]
        return content

    @classmethod
    def from_dict(cls, project_data: dict[str, Any]) -> Self:  # pyright: ignore[reportExplicitAny]
        return cls(**project_data)  # pyright: ignore[reportAny]

    def set_reference_image_path(self, image_path: Path | str):
        if isinstance(image_path, Path):
            self.reference_image_model = ReferenceImageModel(path=str(image_path))
        else:
            self.reference_image_model = ReferenceImageModel(path=image_path)

    def set_shades(self, lut: NDArray[uint8 | uint16]):
        """
        lut -> numpy array of shape (3, X) of integers
        """
        color_data = [Shade.from_pix(tuple(row)) for row in lut]  # pyright: ignore[reportAny]
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

    def set_processing_settings(self, processing_settings: ProcessingSettingsModel):
        copy = processing_settings.model_copy(deep=True)
        self.processing_settings = copy

    def save_as(self, path: str | Path):
        old_path = self.latest_save_path
        self.latest_save_path = str(path)
        try:
            with open(path, "w", encoding="UTF-8") as file:
                json.dump(self.model_dump(), file)
        except OSError as e:
            self.latest_save_path = old_path
            raise e

        # TODO: unify with existing recent_projects system
        _ = add_to_recent_projects(Path(path))

