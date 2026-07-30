from typing import TypeVar, TypeAlias

ColorTable: TypeAlias = list[list[int]]

ShadeTuple: TypeAlias = tuple[int, int, int, int]
PixTuple: TypeAlias = tuple[int, int, int]

Palette: TypeAlias = list[list[int]]

DataRow: TypeAlias = list[int | float | str]
DataTable: TypeAlias = list[DataRow]

ImageElement: TypeAlias = tuple[int, int, str]
DataElement: TypeAlias = tuple[int, int, list[int]]
T = TypeVar("T")


