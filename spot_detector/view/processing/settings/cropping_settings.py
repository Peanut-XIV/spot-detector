from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QPushButton, QSizePolicy, QSpinBox, QWidget
from spot_detector.model.processing_settings_models import CroppingSettings
from spot_detector.view.path_line_widget import PathEdit, PathType
from spot_detector.view.processing.settings.settings_box import BaseSettingsBox, as_checked, is_checked

from pathlib import Path

class CroppingSettingsBox(BaseSettingsBox):

    cropping_test_requested: Signal = Signal(CroppingSettings)

    def __init__(
            self,
            title: str | None = None,
            previous_directory: Path | None = None,
            parent: QWidget | None = None,
            model: CroppingSettings | None = None,
    ):
        super().__init__(title, previous_directory, parent)

        self._init_layout()

        if model is not None:
            self.set_model(model)

        _ = self.test_cropping_button.clicked.connect(self.on_test_requested)


    def _init_layout(self):

        layout: QGridLayout = QGridLayout(self)

        self.enabled_checkbox:     QCheckBox   = QCheckBox("Auto-cropping", self)
        self.save_checkbox:        QCheckBox   = QCheckBox("Save cropped images", self)
        self.save_label:           QLabel      = QLabel("Save path:", self)
        self.save_path:            PathEdit    = PathEdit(PathType.Directory, "Save directory", self._previous_directory, self)
        self.min_radius_checkbox:    QCheckBox   = QCheckBox("minimum radius (% largest inscribed circle)", self)
        self.min_radius_spinbox:     QSpinBox    = QSpinBox(self, suffix="%", minimum=0, maximum=200, value=70)
        self.max_radius_checkbox:    QCheckBox   = QCheckBox("Maximum radius (% largest inscribed circle)", self)
        self.max_radius_spinbox:     QSpinBox    = QSpinBox(self, suffix="%", minimum=0, maximum=200, value=110)
        self.test_cropping_button: QPushButton = QPushButton("Test Cropping on Selection", self)

        self.min_radius_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.max_radius_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.save_path.setMinimumWidth(180)
        self.save_path.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(self.enabled_checkbox,         0, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.save_checkbox,            1, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.save_label,               2, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.save_path,                2, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.save_path.explore_button, 2, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.min_radius_checkbox,      3, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.min_radius_spinbox,       3, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.max_radius_checkbox,      4, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.max_radius_spinbox,       4, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.test_cropping_button,     5, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignCenter)

        _ = self.save_checkbox.checkStateChanged.connect(self.on_do_save_changed)
        _ = self.min_radius_checkbox.checkStateChanged.connect(self.on_min_check_changed)
        _ = self.max_radius_checkbox.checkStateChanged.connect(self.on_max_check_changed)
        _ = self.min_radius_spinbox.valueChanged.connect(self.on_min_value_changed)
        _ = self.max_radius_spinbox.valueChanged.connect(self.on_max_value_changed)

        self.on_do_save_changed(self.save_checkbox.checkState())
        self.on_min_check_changed(self.min_radius_checkbox.checkState())
        self.on_max_check_changed(self.max_radius_checkbox.checkState())

    @Slot(Qt.CheckState)
    def on_do_save_changed(self, checkstate: Qt.CheckState):
        self.save_path.setEnabled(is_checked(checkstate))
        self.save_path.explore_button.setEnabled(is_checked(checkstate))

    @Slot(Qt.CheckState)
    def on_min_check_changed(self, checkstate: Qt.CheckState):
        self.min_radius_spinbox.setEnabled(is_checked(checkstate))

    @Slot(Qt.CheckState)
    def on_max_check_changed(self, checkstate: Qt.CheckState):
        self.max_radius_spinbox.setEnabled(is_checked(checkstate))

    @Slot(int)
    def on_min_value_changed(self, min_value: int):
        max_value = self.max_radius_spinbox.value()
        if min_value > max_value:
            self.max_radius_spinbox.setValue(min_value)

    @Slot(int)
    def on_max_value_changed(self, max_value: int):
        min_value = self.min_radius_spinbox.value()
        if min_value > max_value:
            self.min_radius_spinbox.setValue(max_value)

    def get_model(self) -> CroppingSettings:
        text = self.save_path.text()
        save_path = text if len(text) > 0 else None
        model = CroppingSettings(
            enabled=is_checked(self.enabled_checkbox.checkState()),
            save_cropped_enabled=is_checked(self.save_checkbox.checkState()),
            save_path=save_path,
            min_radius_enabled=is_checked(self.min_radius_checkbox.checkState()),
            min_radius_value=self.min_radius_spinbox.value(),
            max_radius_enabled=is_checked(self.max_radius_checkbox.checkState()),
            max_radius_value=self.max_radius_spinbox.value(),
        )
        return model

    @Slot(CroppingSettings)
    def set_model(self, model: CroppingSettings):
        self.enabled_checkbox.setCheckState(as_checked(model.enabled))
        self.save_checkbox.setCheckState(as_checked(model.save_cropped_enabled))
        self.save_path.setText(model.save_path)
        self.min_radius_checkbox.setCheckState(as_checked(model.min_radius_enabled))
        self.min_radius_spinbox.setValue(model.min_radius_value)
        self.max_radius_checkbox.setCheckState(as_checked(model.max_radius_enabled))
        self.max_radius_spinbox.setValue(model.max_radius_value)

    @Slot()
    def on_test_requested(self) -> None:
        self.cropping_test_requested.emit(self.get_model())
