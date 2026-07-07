from typing import TypeVar, TypeAlias, Union
from enum import IntEnum

ColorTable: TypeAlias = list[list[int]]

ShadeTuple: TypeAlias = tuple[int, int, int, int]
PixTuple: TypeAlias = tuple[int, int, int]

Palette: TypeAlias = list[list[int]]

DataRow: TypeAlias = list[Union[int, float, str]]
DataTable: TypeAlias = list[DataRow]

ImageElement: TypeAlias = tuple[int, int, str]
DataElement: TypeAlias = tuple[int, int, list[int]]
T = TypeVar("T")


class Hint(IntEnum):
    DEFAULT = 0
    COLORS = 1
    MIN_DIST = 2
    THRESH = 3
    AREA = 4
    CIRC = 5
    INERTIA = 6
    CONV = 7
    MISSING = 8
