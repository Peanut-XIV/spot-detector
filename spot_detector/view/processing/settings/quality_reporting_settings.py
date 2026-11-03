from pathlib import Path
from typing import final, override

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from spot_detector.custom_types import ShadeTable
from spot_detector.model.processing_settings_models import QualityReportingSettings
from spot_detector.view.processing.settings.blur_settings_widget import BlurReportingBox
from spot_detector.view.processing.settings.overexposure_settings_widget import (
    OverexposureBox,
)
from spot_detector.view.processing.settings.settings_box import (
    BaseSettingsBox,
    as_checked,
    is_checked,
    recommended_range_tooltip,
)


@final
class QualityReportingBox(BaseSettingsBox):
    quality_test_requested: Signal = Signal(QualityReportingSettings)

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
        self.diameter_spinbox: QSpinBox = QSpinBox(self, minimum=1, maximum=1000, suffix="px")
        self.diameter_spinbox.setToolTip(recommended_range_tooltip("expected_diameter_px"))
        l1.addWidget(self.diameter_spinbox)
        layout.addLayout(l1)

        l2: QHBoxLayout = QHBoxLayout()
        l2.addWidget(QLabel("Collar Fraction", self))
        # Le maximum par defaut de 99.99 rendait une fraction de collier de 1.0
        # inatteignable, alors qu'elle est le haut de la plage documentee.
        self.collar_spinbox: QDoubleSpinBox = QDoubleSpinBox(
            self, minimum=0.0, maximum=100.0, decimals=1, singleStep=5.0, suffix="%"
        )
        self.collar_spinbox.setToolTip(recommended_range_tooltip("collar_fraction", as_percent=True))
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

        # La geometrie de particule appartient a cette boite, parce qu'elle est
        # partagee entre le flou et la surexposition. Les sous-boites la
        # recoivent au lieu de la deviner.
        _ = self.diameter_spinbox.valueChanged.connect(self._push_particle_geometry)
        _ = self.collar_spinbox.valueChanged.connect(self._push_particle_geometry)
        self._push_particle_geometry()

        _ = self.test_reporting_button.clicked.connect(self._request_quality_test)

    @Slot()
    def _request_quality_test(self) -> None:
        # Les reglages partent tels qu'ils sont affiches, pour que l'essai
        # emprunte exactement le chemin du traitement reel.
        self.quality_test_requested.emit(self.get_model())

    @Slot()
    def _push_particle_geometry(self) -> None:
        self.blur_box.set_particle_geometry(
            self.diameter_spinbox.value(),
            self.collar_spinbox.value() / 100,
        )


    @override
    @Slot(object)
    def set_shades(self, shades: ShadeTable | None) -> None:
        super().set_shades(shades)
        self.blur_box.set_shades(shades)
        self.overexposure_box.set_shades(shades)

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
        self._push_particle_geometry()
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
