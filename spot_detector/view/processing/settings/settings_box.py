from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox, QSizePolicy, QWidget
from spot_detector.model.processing_settings_models import BaseProcessingSettings

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
