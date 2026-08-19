from typing import final

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QLabel, QWidget
from spot_detector.model.processing_settings_models import OverExposureDetectionSettings
from spot_detector.view.processing.settings.settings_box import BaseSettingsBox, as_checked, is_checked

from pathlib import Path


@final
class OverexposureBox(BaseSettingsBox):
    def __init__(
            self,
            previous_directory: Path | None = None,
            parent: QWidget | None = None
    ):
        super().__init__("Overexposure reporting", previous_directory, parent)
        self._init_layout()
        self.on_enabled_changed(self.enable_checkbox.checkState())

    def _init_layout(self):
        layout = QGridLayout(self)
        self.enable_checkbox = QCheckBox("Enable overexposure detection")
        self.brightness_sensitivity_spinbox = QDoubleSpinBox(self, minimum=0.0, maximum=100.0, suffix="%")
        self.maximum_area_spinbox = QDoubleSpinBox(self, minimum=0.0, maximum=100.0, suffix="%")

        # Row 0
        layout.addWidget(self.enable_checkbox, 0, 0)
        # Row 1
        layout.addWidget(QLabel("Overexposure sensitivity",self), 1, 0)
        layout.addWidget(self.brightness_sensitivity_spinbox, 1, 1)
        # Row 2
        layout.addWidget(QLabel("Maximum area allowed", self), 2, 0)
        layout.addWidget(self.maximum_area_spinbox, 2, 1)

    def get_model(self) -> OverExposureDetectionSettings:
        model = OverExposureDetectionSettings(
            enabled=is_checked(self.enable_checkbox.checkState()),
            brightness_sensitivity=self.brightness_sensitivity_spinbox.value() / 100,
            area_threshold=self.maximum_area_spinbox.value() / 100,
        )
        return model

    @Slot(object)
    def set_model(self, model: OverExposureDetectionSettings):
        self.enable_checkbox.setCheckState(as_checked(model.enabled))
        self.brightness_sensitivity_spinbox.setValue(100 * model.brightness_sensitivity)
        self.maximum_area_spinbox.setValue(100 * model.area_threshold)
        self.on_enabled_changed(self.enable_checkbox.checkState())

    def on_enabled_changed(self, new_checkstate: Qt.CheckState):
        enabled_state = is_checked(new_checkstate)
        self.brightness_sensitivity_spinbox.setEnabled(enabled_state)
        self.maximum_area_spinbox.setEnabled(enabled_state)
