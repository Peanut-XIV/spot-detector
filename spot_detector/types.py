from typing import TypeVar, TypeAlias, Union

ColorTable:   TypeAlias = list[list[int]]
Palette:      TypeAlias = list[list[int]]
DataRow:      TypeAlias = list[Union[int, float, str]]
DataTable:    TypeAlias = list[DataRow]
ImageElement: TypeAlias = tuple[int, int, str]
DataElement:  TypeAlias = tuple[int, int, list[int]]
T = TypeVar('T')
