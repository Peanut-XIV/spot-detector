from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QGroupBox, QLabel, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget
from spot_detector.model.processing_settings_models import BaseProcessingSettings, CroppingSettings, DustFilterSettings, PreprocessingSettings, ProcessingSettingsModel, QualityReportingSettings
from spot_detector.view.path_line_widget import PathEdit, PathType

from pathlib import Path


def is_checked(state: Qt.CheckState) -> bool:
    match state:
        case Qt.CheckState.Checked:
            return True
        case Qt.CheckState.Unchecked:
            return False
        case Qt.CheckState.PartiallyChecked:
            return False

def as_checked(predicate: bool) -> Qt.CheckState:
    return Qt.CheckState.Checked if predicate else  Qt.CheckState.Unchecked



class BaseSettingsBox(QGroupBox):
    modelChanged: Signal = Signal(BaseProcessingSettings)

    def __init__(
        self,
        title: str | None = None,
        previous_directory: Path | None = None,
        parent: QWidget | None = None,
    ):
        if title is None:
            super().__init__(parent)
        else:
            super().__init__(title, parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._previous_directory: Path = previous_directory or Path.home()



class FilterSettingsBox(BaseSettingsBox):
    dust_filter_test_requested: Signal = Signal(str)
    def __init__(
            self,
            title: str | None = None,
            previous_directory: Path | None = None,
            parent: QWidget | None = None,
            model: DustFilterSettings | None = None,
    ):
        super().__init__(title, previous_directory, parent)

        self._init_layout()

        if model is not None:
            self.set_model(model)

        _ = self.check_filter_button.clicked.connect(self.on_check_requested)

    def _init_layout(self):

        layout: QGridLayout = QGridLayout(self)
        note_text = "Note: The filter and the target images must have the same dimensions"

        self.apply_filter_checkbox:   QCheckBox   = QCheckBox("Apply filter", self)
        self.report_filter_checkbox:  QCheckBox   = QCheckBox("Report filter path", self)
        self.path_label:              QLabel      = QLabel("Filter path:", self)
        self.path_to_filter:          PathEdit    = PathEdit(PathType.ReadOnlyImage, "filter path", self._previous_directory, self)
        self.note_label:              QLabel      = QLabel(note_text, self, alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True)
        self.check_filter_button:     QPushButton = QPushButton("Check files for compatibility", self)
        self.path_to_filter.setMinimumWidth(180)
        self.path_to_filter.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(self.apply_filter_checkbox, 0, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.report_filter_checkbox, 1, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.path_label, 2, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.path_to_filter, 2, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.path_to_filter.explore_button, 2, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.note_label, 3, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.check_filter_button, 4, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.setColumnStretch(1, 2)

    def get_model(self) -> DustFilterSettings:
        text = self.path_to_filter.text()
        filter_path = text if len(text) > 0 else None
        model = DustFilterSettings(
            enabled=is_checked(self.apply_filter_checkbox.checkState()),
            report_path_enabled=is_checked(self.report_filter_checkbox.checkState()),
            path=filter_path
        )
        return model

    @Slot(DustFilterSettings)
    def set_model(self, model: DustFilterSettings):
        self.apply_filter_checkbox.setCheckState(as_checked(model.enabled))
        self.report_filter_checkbox.setCheckState(as_checked(model.report_path_enabled))
        self.path_to_filter.setText(model.path)

    @Slot()
    def on_check_requested(self):
        filter_path = self.path_to_filter.text()
        self.dust_filter_test_requested.emit(filter_path)



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


class QualityReportingBox(BaseSettingsBox):
    def __init__(
            self,
            title: str | None = None,
            previous_directory: Path | None = None,
            parent: QWidget | None = None
    ):
        super().__init__(title, previous_directory, parent)
        self._init_layout()

    def _init_layout(self):

        layout: QGridLayout = QGridLayout(self)

        self.report_overex_checkbox: QCheckBox   = QCheckBox("Report Overexposure",  self)
        self.report_undrex_checkbox: QCheckBox   = QCheckBox("Report Underexposure", self)
        self.report_bright_checkbox: QCheckBox   = QCheckBox("Report brightness",    self)
        self.report_blurry_checkbox: QCheckBox   = QCheckBox("Report blurry images", self)
        self.test_repporting_button: QPushButton = QPushButton("Test Reporting on Selection", self)

        layout.addWidget(self.report_overex_checkbox, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.report_undrex_checkbox, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.report_bright_checkbox, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.report_blurry_checkbox, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.test_repporting_button, 2, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)

    def get_model(self) -> QualityReportingSettings:
        model = QualityReportingSettings(
            report_overexposure=is_checked(self.report_overex_checkbox.checkState()),
            report_underexposure=is_checked(self.report_undrex_checkbox.checkState()),
            report_brightness=is_checked(self.report_bright_checkbox.checkState()),
            report_blurry=is_checked(self.report_blurry_checkbox.checkState()),
        )
        return model

    @Slot(QualityReportingSettings)
    def set_model(self, model: QualityReportingSettings) -> None:
        self.report_overex_checkbox.setCheckState(as_checked(model.report_overexposure))
        self.report_undrex_checkbox.setCheckState(as_checked(model.report_underexposure))
        self.report_bright_checkbox.setCheckState(as_checked(model.report_brightness))
        self.report_blurry_checkbox.setCheckState(as_checked(model.report_blurry))



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
        self.reporting_box: QualityReportingBox = QualityReportingBox("Image Quality Reporting:", self._previous_directory, container)

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
