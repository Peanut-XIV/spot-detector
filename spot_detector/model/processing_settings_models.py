from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Any



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



class QualityReportingSettings(BaseProcessingSettings):
    report_underexposure: bool = Field(default=False)
    report_overexposure: bool = Field(default=False)
    report_brightness: bool = Field(default=False)
    report_blurry: bool = Field(default=False)



class ProcessingOutputSettings(BaseProcessingSettings):
    path: str | None = Field(default=None)
    resume_after_crash_enabled: bool = Field(default=True)



class PreprocessingSettings(BaseProcessingSettings):
    dust_filter: DustFilterSettings = Field()
    cropping: CroppingSettings = Field()
    reporting: QualityReportingSettings = Field()



class UserSelectedDir(BaseProcessingSettings):
    path: str = Field()
    files: list[str] = Field(default_factory=lambda: list())



class ProcessingSettingsModel(BaseProcessingSettings):
    entries: list[str | UserSelectedDir] = Field(default_factory=lambda : list())
    preprocessing: PreprocessingSettings = Field()
    output: ProcessingOutputSettings = Field()
