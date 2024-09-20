from pathlib import Path
from typing import Any, Optional
from typing_extensions import Self
import json
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic_core.core_schema import FieldValidationInfo
import cv2 as cv
from spot_detector.types import ColorTable


class ColorData(BaseModel):
    """
    The datastructure containing both names for labels
    and a table of different colors with the associated
    label number.
    ```
    name = ["label_A", "label_B", "label_C", ...]
    table = [
    #   [bbb, ggg, rrr, ID]  BGR is the standard in openCV, not RGB
        [  0,   0,   0, 0],  # no label (id 0 -> background)
        [255, 255, 255, 1],  # label_A (id 1 -> index 0)
        [  0, 255,   0, 2],  # label_B (id 2 -> index 1)
        [ 12,  25, 255, 3],  # label_C (id 3 -> index 2)
        [ 10, 255,   2, 2],  # Label_B here...
        ...
    ]
    ```
    """
    names: list[str]
    table: ColorTable

    @field_validator("table")
    def validate_table(cls, table: list[list[int]]) -> list[list[int]]:
        if len(table) == 0:
            return table
        test_len = len(table[0])
        for row in table:
            if len(row) != test_len:
                raise ValueError(
                        "color_data.table has inconsistent dimensions"
                )
        for i, row in enumerate(table):
            for j, value in enumerate(row):
                if type(value) is not int:
                    raise ValueError(
                        f"value ({i},{j}) of color_data.table is not an integer"
                    )
        return table
    
    @model_validator(mode="after")
    def check_name_list_match(self) -> Self:
        count = len(self.names)
        for row in self.table:
            if row[-1] > count:
                raise ValidationError("too many labels for too few names")
        return self

    @classmethod
    def from_defaults(cls, color_name) -> Self:
        return cls(names=[color_name], table=[[0, 0, 0, 0],[255,255,255,1]])


class Threshold(BaseModel):
    automatic: bool
    mini: int = Field(ge=0, le=255, default=0)
    maxi: int = Field(ge=0, le=255, default=255)
    step: int = Field(ge=0, le=255, default=16)

    @field_validator("maxi")
    def maxi_greater_than_mini(cls, maxi: int, info: FieldValidationInfo) -> int:
        if maxi <= info.data["mini"]:
            raise ValueError("maxi must be greater than mini")
        return maxi

    @classmethod
    def from_defaults(cls) -> Self:
        return cls(automatic=True)


class SimpleParam(BaseModel):
    enabled: bool
    mini: float = Field(ge=0)
    maxi: Optional[float] = None

    @field_validator("maxi")
    def maxi_greater_than_mini(cls, maxi: Optional[float], info: FieldValidationInfo) -> Optional[float]:
        maxi_does_exist = bool(info.data["enabled"] and (maxi is not None) and maxi)
        try:
            if maxi_does_exist and (maxi <= info.data["mini"]):
                raise ValueError("maxi must be greater than mini")
        except KeyError as ke:
            raise ValueError(f"maxi = {maxi}") from ke
        return maxi


class DetParams(BaseModel):
    """
    The settings of openCV's SimpleBlobDetector, wrapped in
    an object for validation and serialization.
    """
    color_name: str  
    thresh: Threshold
    min_dist: Optional[float] = Field(gt=0, default=None)
    filter_by_color: Optional[int] = Field(ge=0, le=255, default=255)
    area: Optional[SimpleParam] = None
    circ: Optional[SimpleParam] = None
    convex: Optional[SimpleParam] = None
    inertia: Optional[SimpleParam] = None

    def __init__(self, /, **data: Any) -> None:
        super().__init__(**data)

    @classmethod
    def from_defaults(cls, color_name) -> Self:
        return cls(color_name=color_name, thresh=Threshold.from_defaults())

    @classmethod
    def from_prepopulated_defaults(cls, name: str | int | Any) -> Self:
        """
        Returns an instance of DetParams for the settings of a OpenCV
        SimpleBlobDetector instance. Takes the name of the only label as input.
        """
        # base params
        name_str = "undefined_name"
        if isinstance(name, int):
            name_str = f"color_{name}"
        elif isinstance(name, str):
            name_str = name
        thresh = Threshold(automatic=True, mini=0, maxi=255, step=32)
        area = SimpleParam(enabled=True, mini=1.0, maxi=800.0)
        circ = SimpleParam(enabled=True, mini=0.5, maxi=1.0)
        convex = SimpleParam(enabled=True, mini=0.5, maxi=1.0)
        inertia = SimpleParam(enabled=False, mini=0.0, maxi=1.0)
        params = cls(
            color_name=name_str,
            min_dist=1.0,
            filter_by_color=255,
            thresh=thresh,
            area=area,
            circ=circ,
            convex=convex,
            inertia=inertia
        )
        return params

    def load_params(self, shades_count: int) -> cv.SimpleBlobDetector.Params:
        params = cv.SimpleBlobDetector.Params()
        params.blobColor = 255
        if shades_count != 0:
            thresh_step = 255 // shades_count
        else:
            thresh_step = 1
        if self.min_dist is not None:
            minimum_distance: float | int = self.min_dist
            if minimum_distance > 0.0:
                params.minDistBetweenBlobs = self.min_dist
        thresh = self.thresh
        if thresh.automatic:
            params.minThreshold = thresh_step // 4
            params.maxThreshold = 255 - thresh_step // 4
            params.thresholdStep = thresh_step
        else:
            params.minThreshold = thresh.mini
            params.maxThreshold = thresh.maxi
            params.thresholdStep = thresh.step
        area = self.area
        if area is not None and area.enabled:
            params.filterByArea = True
            params.minArea = area.mini
            if area.maxi is not None:
                params.maxArea = area.maxi
        circ = self.circ
        if circ is not None and circ.enabled:
            params.filterByCircularity = True
            params.minCircularity = circ.mini
            if circ.maxi is not None:
                params.maxCircularity = circ.maxi
        convex = self.convex
        if convex is not None and convex.enabled:
            params.filterByConvexity = True
            params.minConvexity = convex.mini
            if convex.maxi is not None:
                params.maxConvexity = convex.maxi
        return params


class ColorAndParams(BaseModel):
    reference_image: str
    color_data: ColorData
    det_params: list[DetParams]

    @classmethod
    def from_defaults(cls) -> Self:
        return cls(
            reference_image = "",
            color_data = ColorData.from_defaults(color_name="color_1"),
            det_params = [DetParams.from_defaults(color_name="color_1")]
        )

    @classmethod
    def from_path(cls, file_path: str | Path) -> Self:
        with open(file_path, "r", encoding="UTF-8") as cfg_file:
            json_dict = json.load(cfg_file)
            content = cls(**json_dict)
        return content


class CLIDefaults(BaseModel):
    image_dir: Optional[str] = None
    csv_path: Optional[str] = None
    depths: Optional[list[str]] = None
    regex: Optional[str] = None

    @classmethod
    def from_path(cls, file_path: str | Path) -> Self:
        """
        Returns the tomlkit table item from
        """
        with open(file_path, "r", encoding="UTF-8") as cfg_file:
            content = json.load(cfg_file).__getitem__("CLI")
        if content is None:
            raise ValidationError(f"CLI not found in file {str(file_path)}")
        output = cls(**content)
        return output
