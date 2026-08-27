from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, Enum
from pathlib import Path
from typing import Callable

from spot_detector.model.config_fingerprint import ProcessingSession

type CellContent = Path | int | float | str | datetime | None

class CheckStatus(Enum):
    Fail = 0
    Success = 1
    Disabled = 2
    NotApplicable = 3

class CheckID(IntEnum):
    Dust_Filter = 0
    ROI = 1
    Sharpness = 2
    Overexposure = 3
    Average_Brightness = 4
    Data_Loss = 5

@dataclass
class CheckReport:
    check_id: CheckID
    check_status: CheckStatus
    check_value: float | int | bool | None
    check_message: str

class ROIStatus(Enum):
    Fail = 0
    Success = 1
    Disabled = 2

@dataclass
class ROIData:
    status: ROIStatus
    center_x: float | None
    center_y: float | None
    radius: float | None

@dataclass
class ImageMetaData:
    creation_date: datetime

    image_format: str
    image_codec: str
    has_lossy_compression: bool
    color_space: str
    subsampling: str

    image_height: int
    image_width: int
    channel_depth: int

    camera_model: str
    exposure_seconds: float


@dataclass
class ImageResult:
    rank: int
    directory: str
    file_name: str
    counts: list[int] | None
    roi_data: ROIData
    checks: dict[CheckID, CheckReport]
    processing_date: datetime
    metadata: ImageMetaData | None
    error: str | None


@dataclass(frozen=True)
class Column:
    name: str
    extract: Callable[[ImageResult, ProcessingSession], CellContent]
