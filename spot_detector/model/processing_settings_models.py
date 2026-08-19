from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo


class BaseProcessingSettings(BaseModel):
    def __init__(self, /, **data: Any) -> None:  # pyright: ignore[reportAny, reportExplicitAny]
        super().__init__(**data)



class DustFilterSettings(BaseProcessingSettings):
    enabled: bool = Field(default=False)
    report_path_enabled: bool = Field(default=False)
    path: str | None = Field(default=None)



class CroppingSettings(BaseProcessingSettings):
    enabled: bool = Field(default=False)
    save_cropped_enabled: bool = Field(default=False)
    save_path: str | None = Field(default=None)
    min_radius_enabled: bool = Field(default=False)
    min_radius_value: int = Field(ge=0, default=0)
    max_radius_enabled: bool = Field(default=False)
    max_radius_value: int = Field(ge=0, default=2000)

    @field_validator("max_radius_value")
    def maxi_greater_than_mini(cls, max_radius_value: int, info: FieldValidationInfo) -> int:
        if max_radius_value < info.data["min_radius_value"]:
            raise ValueError("maxi must be greater than mini")
        return max_radius_value


# Les valeurs par defaut ci-dessous reprennent celles de PARAMETER_RANGES dans
# spot_detector/processing/image_validation/blur_calibration.py, qui reste la
# source documentee des champs de valeur. Elles ne sont pas importees de la
# pour ne pas faire dependre la couche modele d'OpenCV.
class BlurDetectionSettings(BaseProcessingSettings):
    enabled: bool = Field(default=False)
    reference_threshold: float = Field(default=0.10)  # Computed or selected threshold beneath which an image is too blurry
    min_particles: int = Field(ge=0, default=30)
    min_occupation: float = Field(ge=0.0, default=1e-3)


class OverExposureDetectionSettings(BaseProcessingSettings):
    # Le controle de surexposition n'est pas encore implemente : ces deux
    # valeurs ne servent qu'a rendre le bloc constructible tant que enabled
    # est faux, et restent a fixer avec le controle lui-meme.
    enabled: bool = Field(default=False)
    area_threshold: float = Field(default=0.0)  # between 0% overexposed area allowed to 100% overexposed area allowed
    brightness_sensitivity: float = Field(default=0.0)  # proportion of most exposed values considered overexposed


class QualityReportingSettings(BaseProcessingSettings):
    expected_diameter_px: int = Field(ge=0, default=6)  # expected diameter of the bright spots within the image
    collar_fraction: float = Field(ge=0.0, default=0.5)   # fraction of the expected diameter. increases the measured area to better detect blur and overexposure

    blur: BlurDetectionSettings = Field(default_factory=BlurDetectionSettings)
    overexposure: OverExposureDetectionSettings = Field(default_factory=OverExposureDetectionSettings)
    average_brightness: bool = Field(default=False)


class ProcessingOutputSettings(BaseProcessingSettings):
    path: str | None = Field(default=None)
    resume_after_crash_enabled: bool = Field(default=True)


class PreprocessingSettings(BaseProcessingSettings):
    dust_filter: DustFilterSettings = Field(default_factory=DustFilterSettings)
    cropping: CroppingSettings = Field(default_factory=CroppingSettings)
    reporting: QualityReportingSettings = Field(default_factory=QualityReportingSettings)


class UserSelectedDir(BaseProcessingSettings):
    path: str = Field()
    files: list[str] = Field(default_factory=lambda: list())


class ProcessingSettingsModel(BaseProcessingSettings):
    entries: list[str | UserSelectedDir] = Field(default_factory=lambda : list())
    preprocessing: PreprocessingSettings = Field(default_factory=PreprocessingSettings)
    output: ProcessingOutputSettings = Field(default_factory=ProcessingOutputSettings)
