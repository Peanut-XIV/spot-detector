from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from spot_detector.model.processing_settings_models import ProcessingOutputSettings
from spot_detector.view.path_line_widget import PathEdit, PathType

from pathlib import Path

from spot_detector.view.processing.settings.settings_box import as_checked, is_checked


class OutputFilePanel(QWidget):

    def __init__(
        self,
        previous_path: Path | None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)

        self._previous_path: Path = previous_path or Path.home()

        self.setMinimumSize(400, 500)
        self.setBaseSize(400, 600)
        self._init_layout()

    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        label = QLabel("Output Location")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        path_caption = "Choose a file to save the output to"

        output_path_label: QLabel = QLabel("Output file location:", self)
        self.output_path_line: PathEdit = PathEdit(PathType.AnyCSV, path_caption, self._previous_path, self)
        self.output_path_button:  QPushButton = self.output_path_line.explore_button

        path_layout = QHBoxLayout()
        path_layout.addWidget(output_path_label)
        path_layout.addWidget(self.output_path_line)
        path_layout.addWidget(self.output_path_button)
        layout.addLayout(path_layout)

        self.crash_recovery_checkbox: QCheckBox = QCheckBox("Resume interrupted processing on this file", self)
        layout.addWidget(self.crash_recovery_checkbox, alignment=Qt.AlignmentFlag.AlignLeft)

        note_text = "Note: If the given output file already exists, the images reported "\
                   +"as processed will be considered as such and skipped. The output from"\
                   +" processing the remaining files will be added."

        note_label = QLabel(note_text, self, wordWrap=True, alignment=Qt.AlignmentFlag.AlignCenter)
        note_label.setMinimumHeight(100)
        layout.addWidget(note_label, alignment=Qt.AlignmentFlag.AlignCenter)


        layout.addStretch()

    def get_model(self) -> ProcessingOutputSettings:
        model = ProcessingOutputSettings(
            path=self.output_path_line.text(),
            resume_after_crash_enabled=is_checked(self.crash_recovery_checkbox.checkState()),
        )
        return model

    def set_model(self, model: ProcessingOutputSettings) -> None:
        self.output_path_line.setText(model.path)
        self.crash_recovery_checkbox.setCheckState(as_checked(model.resume_after_crash_enabled))
