from typing import final

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QGridLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget
from spot_detector.file_utils import VALID_IMAGE_TYPES
from spot_detector.model.processing_settings_models import BlurDetectionSettings
from spot_detector.view.processing.settings.settings_box import BaseSettingsBox, as_checked, is_checked

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
        self.reference_threshold_spinbox = QDoubleSpinBox(self, minimum=0.0)
        self.min_particle_spinbox = QSpinBox(self, minimum=0)
        self.min_occupation_spinbox = QDoubleSpinBox(self, minimum=0.0, maximum=100.0, suffix="%")

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
        dialog = CalibrateBlurDialog(self._previous_directory, self)
        if dialog.exec():
            thresh = dialog.threshold_value
            if thresh is not None:
                self.reference_threshold_spinbox.setValue(thresh)


@final
class CalibrateBlurDialog(QDialog):
    def __init__(
        self,
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
        self._previous_directory = previous_directory
        self.selected_files: list[Path] = []
        self.threshold_value: float | None = None
        self._init_layout()


    def _init_layout(self):
        layout = QVBoxLayout(self)
        self.compute_button = QPushButton("Compute reference threshold", self)
        self.select_button = QPushButton("Select reference images (0 selected)", self)
        self.maximum_blur_radius_spinbox = QDoubleSpinBox(self, suffix="px", minimum=0)
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
        # TODO: Actually compute the calibrated threshold value





        computed_threshold_value = 0.1
        query_to_user = QMessageBox(
            QMessageBox.Icon.Question,
            "Calibration Done",
            f"The calibrated threshold value is {computed_threshold_value}. Do you wish to apply it?",
            QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel
        )
        if query_to_user.exec():
            self.threshold_value = computed_threshold_value
            self.accept()

