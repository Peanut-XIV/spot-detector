from typing import final

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget
from spot_detector.model.processing_settings_models import QualityReportingSettings
from spot_detector.view.processing.settings.settings_box import BaseSettingsBox, as_checked, is_checked
from spot_detector.view.processing.settings.blur_settings_widget import BlurReportingBox
from spot_detector.view.processing.settings.overexposure_settings_widget import OverexposureBox

from pathlib import Path






@final
class QualityReportingBox(BaseSettingsBox):
    def __init__(
            self,
            previous_directory: Path | None = None,
            parent: QWidget | None = None
    ):
        super().__init__("Quality reporting", previous_directory, parent)
        self._init_layout()

    def _init_layout(self):
        layout: QVBoxLayout = QVBoxLayout(self)

        l1: QHBoxLayout = QHBoxLayout()
        l1.addWidget(QLabel("Expected particle Diameter", self))
        self.diameter_spinbox: QSpinBox = QSpinBox(self, minimum=1, suffix="px")
        l1.addWidget(self.diameter_spinbox)
        layout.addLayout(l1)

        l2: QHBoxLayout = QHBoxLayout()
        l2.addWidget(QLabel("Collar Fraction", self))
        self.collar_spinbox: QDoubleSpinBox = QDoubleSpinBox(self, minimum=0.0, suffix="%")
        l2.addWidget(self.collar_spinbox)
        layout.addLayout(l2)

        layout.addSpacing(20)

        self.blur_box: BlurReportingBox = BlurReportingBox(self._previous_directory, self)
        layout.addWidget(self.blur_box)

        layout.addSpacing(20)

        self.overexposure_box: OverexposureBox = OverexposureBox(self._previous_directory, self)
        layout.addWidget(self.overexposure_box)

        layout.addSpacing(10)

        self.avg_brightness_checkbox: QCheckBox = QCheckBox("Report average brightness", self)
        layout.addWidget(self.avg_brightness_checkbox)

        self.test_reporting_button: QPushButton = QPushButton("Test Reporting on Selection", self)
        layout.addWidget(self.test_reporting_button)


    def get_model(self) -> QualityReportingSettings:
        model = QualityReportingSettings(
            expected_diameter_px=self.diameter_spinbox.value(),
            collar_fraction=self.collar_spinbox.value() / 100,
            blur=self.blur_box.get_model(),
            overexposure=self.overexposure_box.get_model(),
            average_brightness=is_checked(self.avg_brightness_checkbox.checkState())
        )
        return model

    @Slot(object)
    def set_model(self, model: QualityReportingSettings) -> None:
        self.diameter_spinbox.setValue(model.expected_diameter_px)
        self.collar_spinbox.setValue(model.collar_fraction * 100)
        self.blur_box.set_model(model.blur)
        self.overexposure_box.set_model(model.overexposure)
        self.avg_brightness_checkbox.setCheckState(as_checked(model.average_brightness))



if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = QualityReportingBox()
    widget.show()

    sys.exit(app.exec())
