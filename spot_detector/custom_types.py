from typing import Literal
from numpy import (
    ndarray,
    dtype,
    generic,
    int8,
    int16,
    int32,
    int64,
    uint8,
    uint16,
    uint32,
    uint64,
    float32,
    float64,
)

import numpy as np

type ShapeType = (
    tuple[()]
    | tuple[int]
    | tuple[int, int]
    | tuple[int, int, int]
    | tuple[int, int, int, int]
    | tuple[int, int, int, int, int]
    | tuple[int, int, int, int, int, int]
    | tuple[int, ...]
)

type ColorTable = list[list[int]]  # WARN : Deprecated

type ShadeTuple = tuple[int, int, int, int]
type PixTuple   = tuple[int, int, int]

type Palette = list[list[int]]

type DataRow   = list[int | float | str]
type DataTable = list[DataRow]

type ImageElement = tuple[int, int, str]
type DataElement  = tuple[int, int, list[int]]

# Generic NumPy based types
type CommonSInt_T =  int8 |  int16 |  int32 |  int64
type CommonUInt_T = uint8 | uint16 | uint32 | uint64
type CommonInt_T  = CommonSInt_T | CommonUInt_T

type ShapeNVec   = tuple[int]
type ShapeRowVec = tuple[Literal[1], int]
type ShapeMxN    = tuple[int, int]
type ShapeNx4    = tuple[int, Literal[4]]
type ShapeNx3    = tuple[int, Literal[3]]
type ShapeMxNx3  = tuple[int, int, Literal[3]]

type NVec[ScalarT: generic] = ndarray[ShapeNVec, dtype[ScalarT]]
type Array2D[ScalarT: generic] = ndarray[ShapeMxN, dtype[ScalarT]]

type Bool2D   = Array2D[np.bool]
type Float2D  = Array2D[float32]
type Double2D = Array2D[float64]

# Specific Numpy based types
type ImageBGR[ScalarT: generic] = ndarray[ShapeMxNx3, dtype[ScalarT]]
type ImageRGB[ScalarT: generic] = ImageBGR[ScalarT]
type ShadeTable = ndarray[ShapeNx4, dtype[uint16]]    # [b, g, r, category]
type LabelTable[DT: generic] = ndarray[ShapeNx3, dtype[DT]]
