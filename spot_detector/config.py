# Python standard library
from pathlib import Path
from typing import Optional, Any
# Project files
from spot_detector.types import ColorTable
# Other modules
from tomlkit import load, document, table, inline_table, nl, array, aot
from tomlkit.items import Table
from tomlkit.toml_document import TOMLDocument
from pydantic import (Field, BaseModel, TypeAdapter,
                      ValidationError, field_validator)
from pydantic_core.core_schema import FieldValidationInfo
from click import BadParameter


class ColorData(BaseModel):
    names: list[str]
    table: ColorTable

    @field_validator("table")
    def table_values_are_chars(cls,
                               table: ColorTable,
                               ) -> ColorTable:
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
    def maxi_greater_than_mini(cls,
                               maxi: int,
                               info: FieldValidationInfo,
                               ) -> int:
        if maxi <= info.data["mini"]:
            raise ValueError("maxi must be greater than mini")
        return maxi


class SimpleParam(BaseModel):
    enabled: bool
    mini: float = Field(ge=0)
    maxi: Optional[float] = None

    @field_validator("maxi")
    def maxi_greater_than_mini(cls,
                               maxi: Optional[float],
                               info: FieldValidationInfo,
                               ) -> Optional[float]:
        maxi_does_exist = bool(info.data["enabled"]
                               and (maxi is not None)
                               and maxi)
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
    convex: Optional[SimpleParam] = None
    inertia: Optional[SimpleParam] = None


class ColorAndParams(BaseModel):
    reference_image: str
    color_data: ColorData
    det_params: list[DetParams]


class CLIDefaults(BaseModel):
    image_dir: Optional[str] = None
    csv_path: Optional[str] = None
    depths: Optional[list[str]] = None
    regex: Optional[str] = None


def get_color_and_params(file_path: str | Path) -> ColorAndParams:
    content = None
    with open(file_path, "r", encoding="UTF-8") as cfg_file:
        content = load(cfg_file)
    ta = TypeAdapter(ColorAndParams)
    try:
        ta.validate_python(content)
    except ValidationError as e:
        print(e)
    return content


def get_cli_defaults(file_path: str | Path) -> CLIDefaults:
    content = None
    with open(file_path, "r") as cfg_file:
        content = load(cfg_file).get("CLI")
    ta = TypeAdapter(CLIDefaults)
    try:
        ta.validate_python(content)
    except ValidationError as e:
        print(e)
    return content


def default_det_params(name: str | int | Any) -> Table:
    params = table()
    # base params
    name_str = "undefined_name"
    if type(name) is int:
        name_str = f"color_{name}"
    elif type(name) is str:
        name_str = name
    params.add("color_name", name_str)
    params.add("min_dist", 0.0)
    params.add("filter_by_color", 255)
    # thresh
    thresh = inline_table()
    thresh.add("automatic", True)
    thresh.add("mini", 0)
    thresh.add("maxi", 255)
    thresh.add("step", 32)
    params.add("thresh", thresh)
    # area
    area = inline_table()
    area.add("enabled", True)
    area.add("mini", 0.0)
    area.add("maxi", 800.0)
    params.add("area", area)
    # circularity
    circ = inline_table()
    circ.add("enabled", True)
    circ.add("mini", 0.5)
    circ.add("maxi", 1.0)
    params.add("cir", circ)
    # convexity
    convex = inline_table()
    convex.add("enabled", True)
    convex.add("mini", 0.5)
    convex.add("maxi", 1.0)
    params.add("convex", convex)
    # Inertia
    inertia = inline_table()
    inertia.add("enabled", False)
    inertia.add("mini", 0.0)
    inertia.add("maxi", 1.0)
    params.add("inertia", inertia)
    params.add(nl())
    return params


def create_new_config() -> TOMLDocument:
    config = document()
    config["reference_image"] = ""
    config.add(nl())  # ----------------------
    color_data = table()
    color_data.add("names", ["lighter"])
    color_table = array()
    color_table.multiline(True)
    color_table.add_line(array("[0, 0, 0, 0]"))
    color_table.add_line(array("[255, 255, 255, 1]"))
    color_data.add("table", color_table)
    config.add("color_data", color_data)
    config.add(nl())  # ----------------------
    det_params = aot()
    det_params.extend([default_det_params("lighter")])
    config.add("det_params", det_params)
    return config


def get_defaults_or_error(defaults_file: str | Path) -> CLIDefaults:
    try:
        defaults = get_cli_defaults(defaults_file)
    except ValidationError as e:
        e2 = BadParameter("Le fichier de valeurs par"
                          " défaut n'est pas valide",
                          param_hint=["-d"])
        raise e2 from e
    return defaults
