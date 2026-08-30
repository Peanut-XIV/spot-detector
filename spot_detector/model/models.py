from enum import Enum
from pathlib import Path
from typing import Any
from typing_extensions import Self
import json
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_core.core_schema import FieldValidationInfo
import cv2 as cv
from spot_detector.custom_types import PixTuple, ShadeTuple


class ChannelOrder(Enum):
    RGB = 0
    BGR = 1


class ChannelDepth(Enum):
    U8 = 0
    U16 = 1


class Shade(BaseModel):
    b: int = Field(ge=0, lt=65536)
    g: int = Field(ge=0, lt=65536)
    r: int = Field(ge=0, lt=65536)
    label_id: int = Field(ge=0)

    @classmethod
    def from_row(cls, row: ShadeTuple) -> Self:
        return cls(b=row[0], g=row[1], r=row[2], label_id=row[3])

    @classmethod
    def from_pix(cls, pix: PixTuple, label_id: int = 0) -> Self:
        return cls(b=pix[0], g=pix[1], r=pix[2], label_id=label_id)

    @classmethod
    def with_conversion(
        cls,
        values: PixTuple,
        label_id: int,
        input_order: ChannelOrder = ChannelOrder.BGR,
        input_depth: ChannelDepth = ChannelDepth.U16,
    ):
        if input_order == ChannelOrder.RGB:
            values = (values[2], values[1], values[0])

        if input_depth == ChannelDepth.U8:
            values = (
                values[0] << 8,
                values[1] << 8,
                values[2] << 8,
            )

        return cls(b=values[0], g=values[1], r=values[2], label_id=label_id)

    def get_color(
        self,
        order: ChannelOrder = ChannelOrder.BGR,
        depth: ChannelDepth = ChannelDepth.U16,
    ):
        if order == ChannelOrder.RGB:
            val = (self.r, self.g, self.b)
        else:
            val = (self.b, self.g, self.r)

        if depth == ChannelDepth.U8:
            val = (
                val[0] >> 8,
                val[1] >> 8,
                val[2] >> 8,
            )

        return val

    @property
    def rgb_u8(self):
        return (
            self.r >> 8,
            self.g >> 8,
            self.b >> 8,
        )

    def set_color(
        self,
        values: PixTuple,
        order: ChannelOrder = ChannelOrder.BGR,
        depth: ChannelDepth = ChannelDepth.U16,
    ):
        if order == ChannelOrder.RGB:
            values = (values[2], values[1], values[0])

        if depth == ChannelDepth.U8:
            values = (
                values[0] << 8,
                values[1] << 8,
                values[2] << 8,
            )
        self.b, self.g, self.r = values

    def set_red(self, red_value: int):
        if not (0 <= red_value < 65536):
            raise ValueError()
        self.r = red_value

    def set_green(self, green_value: int):
        if not (0 <= green_value < 65536):
            raise ValueError()
        self.g = green_value

    def set_blue(self, blue_value: int):
        if not (0 <= blue_value < 65536):
            raise ValueError()
        self.b = blue_value

    def get_label_id(self) -> int:
        return self.label_id

    def set_label_id(self, id: int):
        if id < 0:
            raise ValueError("ValueError: Expected a positive integer value")
        self.label_id = id

    def as_row(self) -> ShadeTuple:
        return (self.b, self.g, self.r, self.label_id)


def homogenous_color_table(levels: int) -> list[ShadeTuple]:
    """
    create a table of well-spread values.
    The returned ColorTable contains `levels` cubed rows.
    Values for `levels` above 5 are not recommended.
    """
    base = [int(i * 65535 / (levels - 1)) for i in range(levels)]
    table: list[ShadeTuple] = []
    id = 0
    for x in base:
        for y in base:
            for z in base:
                table.append((x, y, z, id))
                id += 1
    return table


class SimpleParam(BaseModel):
    enabled: bool
    mini: float = Field(ge=0, default=0)
    maxi: float | None = None

    def __init__(self, /, **data: Any) -> None:  # pyright: ignore[reportExplicitAny, reportAny]
        super().__init__(**data)

    @field_validator("maxi")
    def maxi_greater_than_mini(
        cls, maxi: float | None, info: FieldValidationInfo
    ) -> float | None:
        maxi_does_exist = bool(info.data["enabled"] and (maxi is not None) and maxi)
        try:
            if maxi_does_exist and (maxi <= info.data["mini"]):
                raise ValueError("maxi must be greater than mini")
        except KeyError as ke:
            raise ValueError(f"maxi = {maxi}") from ke
        return maxi

    @classmethod
    def from_defaults(cls, enabled: bool, mini: float, maxi: float | None) -> Self:
        return cls(enabled=enabled, mini=mini, maxi=maxi)


class DetParams(BaseModel):
    """
    The settings of openCV's SimpleBlobDetector, wrapped in
    an object for validation and serialization.
    """

    color_name: str
    min_dist: float | None = Field(gt=0, default=None)
    area:    SimpleParam = Field(default_factory=lambda: SimpleParam.from_defaults(False, 0, 4000))
    circ:    SimpleParam = Field(default_factory=lambda: SimpleParam.from_defaults(False, 0, 1))
    convex:  SimpleParam = Field(default_factory=lambda: SimpleParam.from_defaults(False, 0, 1))

    def __init__(self, /, **data: Any) -> None:  # pyright: ignore[reportExplicitAny, reportAny]
        super().__init__(**data)

    @classmethod
    def from_defaults(cls, color_name: str) -> Self:
        return cls(color_name=color_name)

    @classmethod
    def from_prepopulated_defaults(cls, name: str | int | None) -> Self:
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
        area = SimpleParam(enabled=True, mini=1.0, maxi=800.0)
        circ = SimpleParam(enabled=True, mini=0.5, maxi=1.0)
        convex = SimpleParam(enabled=True, mini=0.5, maxi=1.0)
        params = cls(
            color_name=name_str,
            min_dist=1.0,
            area=area,
            circ=circ,
            convex=convex,
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

        params.minThreshold = thresh_step // 4
        params.maxThreshold = 255 - thresh_step // 4
        params.thresholdStep = thresh_step

        area = self.area
        if area.enabled:
            params.filterByArea = True
            params.minArea = area.mini
            if area.maxi is not None:
                params.maxArea = area.maxi
        else:
            params.filterByArea = False

        circ = self.circ
        if circ.enabled:
            params.filterByCircularity = True
            params.minCircularity = circ.mini
            if circ.maxi is not None:
                params.maxCircularity = circ.maxi
        else:
            params.filterByCircularity = False

        convex = self.convex
        if convex.enabled:
            params.filterByConvexity = True
            params.minConvexity = convex.mini
            if convex.maxi is not None:
                params.maxConvexity = convex.maxi
        else:
            params.filterByConvexity = False
        return params


class ColorAndParams(BaseModel):
    shades: list[Shade]
    det_params: list[DetParams]

    @classmethod
    def from_defaults(cls, color_name: str = "color_1") -> Self:
        return cls(
            shades=[Shade.from_row(row) for row in homogenous_color_table(2)],
            det_params=[DetParams.from_defaults(color_name)],
        )

    @classmethod
    def from_prepopulated_defaults(cls, color_name: str = "color_1") -> Self:
        return cls(
            shades=[Shade.from_row(row) for row in homogenous_color_table(2)],
            det_params=[DetParams.from_prepopulated_defaults(color_name)],
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:  # pyright: ignore[reportExplicitAny]
        return cls(**data)  # pyright: ignore[reportAny]

    def generate_detection_parameters(self):
        """
        Adds DetParams objects as well as color names to the det_params and
        color name lists in order to match the maximum label id in the color
        data table. This allows for additional / optional sets of detection
        parameters.
        """
        # TODO: complete function
        ...

    def swap_params(self, index_1: int, index_2: int):
        """
        swaps two det_params's position as well as their names.
        if the indices do not fit, raises an IndexError.
        """
        # Trivial case
        if index_1 == index_2:
            return

        # handle IndexErrors
        length = len(self.det_params)
        idx1_inrange = -length <= index_1 < length
        idx2_inrange = -length <= index_2 < length

        if (not idx1_inrange) or (not idx2_inrange):
            errmsg = "OutOfRangeError: "

            if index_1 < -length:
                errmsg += f"(index_1(={index_1}) < -length(={-length}))"
            elif index_1 >= length:
                errmsg += f"(index_1(={index_1}) >= length(={length}))"

            if not (idx1_inrange and idx2_inrange):
                errmsg += " and "

            if index_2 < -length:
                errmsg += f"(index_2(={index_2}) < -length(={-length}))"
            elif index_2 >= length:
                errmsg += f"(index_2(={index_2}) >= length(={length}))"

            raise IndexError(errmsg)

        # we are free to continue without error
        temp_det_1 = self.det_params[index_1]
        self.det_params[index_1] = self.det_params[index_2]
        self.det_params[index_2] = temp_det_1

    @property
    def color_names(self):
        return [det_param.color_name for det_param in self.det_params]

    def append_new_color(self, name: str):
        self.det_params.append(DetParams.from_defaults(name))


class CLIDefaults(BaseModel):
    image_dir: str | None = None
    csv_path: str | None = None
    depths: list[str] | None = None
    regex: str | None = None

    @classmethod
    def from_path(cls, file_path: str | Path) -> Self:
        """
        Unused code, check before removing though
        """
        with open(file_path, "r", encoding="UTF-8") as cfg_file:
            content = json.load(cfg_file).__getitem__("CLI")  # pyright: ignore[reportAny]
        if content is None:
            raise ValidationError(f"CLI not found in file {str(file_path)}")
        output = cls(**content)  # pyright: ignore[reportAny]
        return output
