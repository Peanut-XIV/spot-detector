from typing import final

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QGridLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget
from spot_detector.file_utils import VALID_IMAGE_TYPES
from spot_detector.model.processing_settings_models import BlurDetectionSettings
from spot_detector.controller.worker_thread import BlurCalibrationProcessor
from spot_detector.processing.image_validation.blur_calibration import BlurCalibration
from spot_detector.types import ShadeTable
from spot_detector.view.processing.settings.settings_box import (
    BaseSettingsBox,
    as_checked,
    is_checked,
    recommended_range_tooltip,
)

from pathlib import Path

@final
class BlurReportingBox(BaseSettingsBox):
    def __init__(
            self,
            previous_directory: Path | None = None,
            parent: QWidget | None = None
    ):
        super().__init__("Blur reporting", previous_directory, parent)
        self._init_layout()

        _ = self.enable_checkbox.checkStateChanged.connect(self.on_enabled_changed)
        _ = self.calibrate_threshold_button.clicked.connect(self.run_calibration)

        self.on_enabled_changed(self.enable_checkbox.checkState())


    def _init_layout(self):

        layout = QGridLayout(self)

        self.enable_checkbox = QCheckBox("Enable blur detection")
        self.calibrate_threshold_button = QPushButton("Calibrate", self)

        # QDoubleSpinBox vaut par defaut decimals=2 et maximum=99.99, ce qui
        # tronque un seuil calibre de 0.112 a 0.11 et une occupation de
        # 8.3e-4 a 8e-4. Les deux sont donc fixes explicitement, sur des bornes
        # plus larges que la plage recommandee rappelee en infobulle.
        self.reference_threshold_spinbox = QDoubleSpinBox(
            self, minimum=0.0, maximum=100.0, decimals=4, singleStep=0.001
        )
        self.min_particle_spinbox = QSpinBox(self, minimum=0, maximum=10000)
        self.min_occupation_spinbox = QDoubleSpinBox(
            self, minimum=0.0, maximum=100.0, decimals=4, singleStep=0.01, suffix="%"
        )

        self.reference_threshold_spinbox.setToolTip(
            recommended_range_tooltip("reference_threshold")
        )
        self.min_particle_spinbox.setToolTip(
            recommended_range_tooltip("min_particles")
        )
        self.min_occupation_spinbox.setToolTip(
            recommended_range_tooltip("min_occupation", as_percent=True)
        )

        # Row 0
        layout.addWidget(self.enable_checkbox, 0, 0)
        # Row 1
        layout.addWidget(QLabel("Reference threshold:", self), 1, 0)
        layout.addWidget(self.calibrate_threshold_button, 1, 1)
        layout.addWidget(self.reference_threshold_spinbox, 1, 2)
        # Row 2
        layout.addWidget(QLabel("Minimum particle count", self), 2, 0)
        layout.addWidget(self.min_particle_spinbox, 2, 1, 1, 2)
        # Row 3
        layout.addWidget(QLabel("Minimum covered area", self), 3, 0)
        layout.addWidget(self.min_occupation_spinbox, 3, 1, 1, 2)

    def get_model(self):
        model = BlurDetectionSettings(
            enabled  = is_checked(self.enable_checkbox.checkState()),
            reference_threshold = self.reference_threshold_spinbox.value(),
            min_particles       = self.min_particle_spinbox.value(),
            min_occupation      = self.min_occupation_spinbox.value() / 100
        )
        return model

    @Slot(object)
    def set_model(self, model: BlurDetectionSettings):
        self.enable_checkbox.setCheckState(as_checked(model.enabled))
        self.reference_threshold_spinbox.setValue(model.reference_threshold)
        self.min_particle_spinbox.setValue(model.min_particles)
        self.min_occupation_spinbox.setValue(model.min_occupation * 100)
        self.on_enabled_changed(self.enable_checkbox.checkState())

    @Slot(Qt.CheckState)
    def on_enabled_changed(self, new_checkstate: Qt.CheckState):
        enabled_state = is_checked(new_checkstate)
        self.calibrate_threshold_button.setEnabled(enabled_state)
        self.reference_threshold_spinbox.setEnabled(enabled_state)
        self.min_particle_spinbox.setEnabled(enabled_state)
        self.min_occupation_spinbox.setEnabled(enabled_state)

    @Slot()
    def run_calibration(self):
        if self._shades is None:
            _ = QMessageBox.warning(
                self,
                "No palette available",
                "The blur threshold is calibrated against the project palette, "
                "which is not available here. Define the project shades first.",
            )
            return

        dialog = CalibrateBlurDialog(self._shades, self._previous_directory, self)
        if dialog.exec():
            thresh = dialog.threshold_value
            if thresh is not None:
                self.reference_threshold_spinbox.setValue(thresh)


@final
class CalibrateBlurDialog(QDialog):
    def __init__(
        self,
        shades: ShadeTable,
        /,
        previous_directory: Path | None = None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Dialog,
        *,
        sizeGripEnabled: bool | None = False,
        modal: bool | None = True,
    ) -> None:
        super().__init__(parent, f, sizeGripEnabled=sizeGripEnabled, modal=modal)
        self.setWindowTitle("Blur detection calibration")
        self._shades: ShadeTable = shades
        self._previous_directory = previous_directory
        self.selected_files: list[Path] = []
        self.threshold_value: float | None = None
        self.calibration: BlurCalibration | None = None
        self._thread: BlurCalibrationProcessor | None = None
        self._init_layout()


    def _init_layout(self):
        layout = QVBoxLayout(self)
        self.compute_button = QPushButton("Compute reference threshold", self)
        self.select_button = QPushButton("Select reference images (0 selected)", self)
        self.maximum_blur_radius_spinbox = QDoubleSpinBox(
            self, suffix="px", minimum=0.0, maximum=100.0, decimals=2, singleStep=0.1
        )
        # Rayon du flou gaussien de rejet, celui qu'une image tout juste
        # inacceptable presenterait. C'est le reject_sigma de calibrate_blur.
        self.maximum_blur_radius_spinbox.setValue(1.5)
        self.cancel_button = QPushButton("Cancel", self)

        layout.addWidget(self.select_button)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Maximum acceptable blur radius:", self))
        layout.addWidget(self.maximum_blur_radius_spinbox)
        layout.addWidget(self.compute_button)
        layout.addSpacing(20)
        layout.addWidget(self.cancel_button)

        _ = self.select_button.clicked.connect(self._on_select_files)
        _ = self.compute_button.clicked.connect(self._on_compute_threshold)
        _ = self.cancel_button.clicked.connect(self.reject)

    def _on_select_files(self):
        select_files_dialog = QFileDialog(
            self,
            "Select reference files",
            str(self._previous_directory),
            VALID_IMAGE_TYPES,
            viewMode=QFileDialog.ViewMode.Detail,
            fileMode=QFileDialog.FileMode.ExistingFiles,
            acceptMode=QFileDialog.AcceptMode.AcceptOpen,
        )

        if select_files_dialog.exec():
            self.selected_files = [Path(file) for file in select_files_dialog.selectedFiles()]
            file_count = len(self.selected_files)
            self.select_button.setText(f"Select reference images ({file_count} selected)")

    def _on_compute_threshold(self):
        if not self.selected_files:
            _ = QMessageBox.warning(
                self,
                "No reference image",
                "Select at least one sharp reference image before calibrating.",
            )
            return

        self._set_busy(True)

        thread = BlurCalibrationProcessor(
            self.selected_files,
            self._shades,
            reject_sigma=self.maximum_blur_radius_spinbox.value(),
            parent=self,
        )
        _ = thread.result_ready.connect(self._on_calibration_ready)
        _ = thread.failed.connect(self._on_calibration_failed)
        _ = thread.finished.connect(lambda: self._set_busy(False))
        _ = thread.finished.connect(thread.deleteLater)

        self._thread = thread
        thread.start()

    def _set_busy(self, busy: bool) -> None:
        self.compute_button.setEnabled(not busy)
        self.select_button.setEnabled(not busy)
        self.maximum_blur_radius_spinbox.setEnabled(not busy)
        self.compute_button.setText(
            "Computing..." if busy else "Compute reference threshold"
        )

    @Slot(str)
    def _on_calibration_failed(self, message: str) -> None:
        _ = QMessageBox.warning(self, "Calibration failed", message)

    @Slot(object)
    def _on_calibration_ready(self, calibration: BlurCalibration) -> None:
        self.calibration = calibration

        details = (
            f"The calibrated threshold value is {calibration.reference_threshold:.4f}.\n"
            + f"Minimum occupation: {calibration.min_occupation:.2e}\n"
            + f"Collar: {calibration.chosen_collar_px} px "
            + f"(expected diameter {calibration.expected_diameter_px} px)\n"
            + f"Sharp scores: {[round(score, 4) for score in calibration.sharp_scores]}\n"
            + f"Blurred scores: {[round(score, 4) for score in calibration.blurred_scores]}"
        )
        if calibration.warnings:
            details += "\n\n" + "\n".join(calibration.warnings)
        details += "\n\nDo you wish to apply it?"

        query_to_user = QMessageBox(
            QMessageBox.Icon.Question,
            "Calibration Done",
            details,
            QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel,
            self,
        )
        # exec rend l'identifiant du bouton clique, non nul dans les deux cas :
        # un simple test de verite appliquait le seuil meme sur Cancel.
        if query_to_user.exec() == QMessageBox.StandardButton.Apply:
            self.threshold_value = calibration.reference_threshold
            self.accept()

