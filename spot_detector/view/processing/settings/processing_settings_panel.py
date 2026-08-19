from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget
from spot_detector.model.processing_settings_models import PreprocessingSettings
from spot_detector.view.processing.settings.filter_settings import FilterSettingsBox
from spot_detector.view.processing.settings.cropping_settings import CroppingSettingsBox
from spot_detector.view.processing.settings.quality_reporting_settings import QualityReportingBox

from pathlib import Path



class ProcessingSettingsPanel(QWidget):

    def __init__(
        self,
        previous_directory: Path | None = None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self.setMinimumSize(400, 500)
        self.setBaseSize(400, 600)

        self._previous_directory: Path = previous_directory or Path.home()

        self._init_layout()

    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        label = QLabel("Preprocessing Settings")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        container = QWidget(scroll_area)

        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)

        self.filter_box: FilterSettingsBox = FilterSettingsBox("Dust Filter:", self._previous_directory, container)
        self.cropping_box: CroppingSettingsBox = CroppingSettingsBox("Automatic Cropping:", self._previous_directory, container)
        self.reporting_box: QualityReportingBox = QualityReportingBox(self._previous_directory, container)

        self.filter_box.setMinimumHeight(220)
        self.cropping_box.setMinimumHeight(220)
        self.reporting_box.setMinimumHeight(150)

        container_layout.addWidget(self.filter_box)
        container_layout.addWidget(self.cropping_box)
        container_layout.addWidget(self.reporting_box)

        scroll_area.setWidget(container)

        layout.addWidget(scroll_area)

    def get_model(self) -> PreprocessingSettings:
        model = PreprocessingSettings(
            dust_filter=self.filter_box.get_model(),
            cropping=self.cropping_box.get_model(),
            reporting=self.reporting_box.get_model(),
        )
        return model

    @Slot(PreprocessingSettings)
    def set_model(self, model: PreprocessingSettings) -> None:
        self.filter_box.set_model(model.dust_filter)
        self.cropping_box.set_model(model.cropping)
        self.reporting_box.set_model(model.reporting)
