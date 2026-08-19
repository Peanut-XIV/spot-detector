from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox, QSizePolicy, QWidget
from spot_detector.model.processing_settings_models import BaseProcessingSettings
from spot_detector.processing.image_validation.blur_calibration import PARAMETER_RANGES

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


def recommended_range_tooltip(name: str, as_percent: bool = False) -> str:
    """Infobulle rappelant le champ de valeur documente d'un parametre.

    PARAMETER_RANGES est la source unique de ces plages : les bornes des
    widgets sont volontairement plus larges, pour qu'une calibration sortant
    de la plage recommandee reste representable plutot que tronquee.
    """
    minimum, maximum, default, unit, description = PARAMETER_RANGES[name]

    if as_percent:
        minimum, maximum, default = minimum * 100, maximum * 100, default * 100
        unit = "%"

    unit_suffix = "" if unit in ("-", "") else f" {unit}"

    return (
        f"{description}\n"
        + f"Recommended range: {minimum:g} to {maximum:g}{unit_suffix} "
        + f"(default {default:g}{unit_suffix})"
    )



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
