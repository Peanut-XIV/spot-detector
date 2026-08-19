from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QPushButton, QSizePolicy, QWidget
from spot_detector.model.processing_settings_models import DustFilterSettings
from spot_detector.view.path_line_widget import PathEdit, PathType
from spot_detector.view.processing.settings.settings_box import BaseSettingsBox, is_checked, as_checked

from pathlib import Path

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
