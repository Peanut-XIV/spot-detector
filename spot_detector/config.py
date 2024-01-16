# Python standard library
from pathlib import Path
from typing import TypeAlias, Optional
# Other modules
from tomlkit import load
from pydantic import (Field, BaseModel, TypeAdapter,
                      ValidationError, field_validator)
from pydantic_core.core_schema import FieldValidationInfo

RawColorTable: TypeAlias = list[list[int]]


class ColorData(BaseModel):
    names: list[str]
    table: list[list[int]]

    @field_validator("table")
    def table_values_are_chars(cls, table):
        for i, row in enumerate(table):
            for j, value in enumerate(row):
                if type(value) is not int:
                    raise ValueError(f"value ({i},{j}) of color_data.table "
                                     "is not between 0 and 255 (inclusive)")
        return table


class Threshold(BaseModel):
    automatic: bool
    mini: int = Field(ge=0, le=255, default=0)
    maxi: int = Field(ge=0, le=255, default=255)
    step: int = Field(ge=0, le=255, default=16)

    @field_validator("maxi")
    def maxi_greater_than_mini(cls, maxi, info: FieldValidationInfo):
        if maxi <= info.data["mini"]:
            raise ValueError("maxi must be greater than mini")
        return maxi


class SimpleParam(BaseModel):
    enabled: bool
    mini: float = Field(ge=0)
    maxi: Optional[float] = None

    @field_validator("maxi")
    def maxi_greater_than_mini(cls, maxi, info: FieldValidationInfo):
        maxi_does_exist = (
            info.data["enabled"]
            and (maxi is not None)
            and maxi
        )
        try:
            if maxi_does_exist and (maxi <= info.data["mini"]):
                raise ValueError("maxi must be greater than mini")
        except KeyError:
            raise ValueError(f"maxi = {maxi}")
        return maxi


class DetParams(BaseModel):
    color_name: str
    thresh: Threshold
    min_dist: Optional[float] = Field(ge=0, default=None)
    area: Optional[SimpleParam] = None
    circ: Optional[SimpleParam] = None
    conv: Optional[SimpleParam] = None


class ColorAndParams(BaseModel):
    color_data: ColorData
    det_params: list[DetParams]


class CLIDefaults(BaseModel):
    image_dir: Optional[str] = None
    csv_path: Optional[str] = None
    depths: Optional[list[str]] = None
    regex: Optional[str] = None


def incoherent_file(file_path: str, should_exist: bool):
    obj = Path(file_path)
    is_file = obj.exists() and obj.is_file()
    return is_file == should_exist


def get_color_and_params(file_path) -> dict:
    content = None
    with open(file_path, "r", encoding="UTF-8") as cfg_file:
        content: dict = load(cfg_file)
    ta = TypeAdapter(ColorAndParams)
    try:
        ta.validate_python(content)
    except ValidationError as e:
        print(e)
    return content


def get_cli_defaults(file_path) -> dict:
    content = None
    with open(file_path, "r") as cfg_file:
        content = load(cfg_file).get("CLI")
    ta: dict = TypeAdapter(CLIDefaults)
    try:
        ta.validate_python(content)
    except ValidationError as e:
        print(e)
    return content


def get_det_params_defaults(file_path) -> dict:
    content = None
    with open(file_path, "r") as cfg_file:
        content = load(cfg_file).get("det_params")
    ta = TypeAdapter(DetParams)
    try:
        ta.validate_python(content)
    except ValidationError as e:
        print(e)
    return content
