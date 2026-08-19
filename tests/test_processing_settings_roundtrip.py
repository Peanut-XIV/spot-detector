"""Aller-retour des reglages de traitement a travers un fichier .spot.

Le bloc de report qualite a gagne des champs obligatoires en cours de route,
ce qui rendait illisible tout projet enregistre avec la forme precedente. Ces
verifications tiennent le format : un projet complet doit se relire a
l'identique, et un projet ecrit avant l'ajout d'un champ doit encore s'ouvrir.
"""

import json
import sys
import tempfile
from pathlib import Path

from spot_detector.model.processing_settings_models import (
    BlurDetectionSettings,
    OverExposureDetectionSettings,
    PreprocessingSettings,
    ProcessingOutputSettings,
    ProcessingSettingsModel,
    QualityReportingSettings,
)
from spot_detector.model.project import Project


def calibrated_settings() -> ProcessingSettingsModel:
    """Les valeurs de la calibration V3, celles qui doivent survivre au
    passage par le fichier sans etre arrondies."""
    return ProcessingSettingsModel(
        entries=[],
        preprocessing=PreprocessingSettings(
            reporting=QualityReportingSettings(
                expected_diameter_px=4,
                collar_fraction=0.5,
                blur=BlurDetectionSettings(
                    enabled=True,
                    reference_threshold=0.112,
                    min_particles=30,
                    min_occupation=8.3e-4,
                ),
                overexposure=OverExposureDetectionSettings(),
                average_brightness=True,
            ),
        ),
        output=ProcessingOutputSettings(),
    )


def test_full_roundtrip(directory: Path) -> None:
    project = Project(name="essai")
    project.set_processing_settings(calibrated_settings())

    path = directory / "complet.spot"
    project.save_as(path)
    reloaded = Project.from_path(path)

    assert reloaded.processing_settings == project.processing_settings, (
        "les reglages ne se relisent pas a l'identique"
    )

    blur = reloaded.processing_settings.preprocessing.reporting.blur
    assert blur.reference_threshold == 0.112, blur.reference_threshold
    assert blur.min_occupation == 8.3e-4, blur.min_occupation
    print("aller-retour complet          : ok")


def test_missing_reporting_block(directory: Path) -> None:
    """Un projet enregistre avant l'ajout du bloc qualite doit s'ouvrir."""
    project = Project(name="essai")
    project.set_processing_settings(calibrated_settings())
    path = directory / "sans_bloc.spot"
    project.save_as(path)

    data = json.loads(path.read_text(encoding="UTF-8"))
    del data["processing_settings"]["preprocessing"]["reporting"]
    path.write_text(json.dumps(data), encoding="UTF-8")

    reporting = Project.from_path(path).processing_settings.preprocessing.reporting
    assert reporting.expected_diameter_px == 6, reporting.expected_diameter_px
    assert reporting.blur.enabled is False
    print("bloc qualite absent           : ok")


def test_previous_reporting_shape(directory: Path) -> None:
    """La forme precedente du bloc, quatre booleens report_*, doit encore
    s'ouvrir sur les valeurs par defaut plutot que d'echouer."""
    project = Project(name="essai")
    project.set_processing_settings(calibrated_settings())
    path = directory / "ancienne_forme.spot"
    project.save_as(path)

    data = json.loads(path.read_text(encoding="UTF-8"))
    data["processing_settings"]["preprocessing"]["reporting"] = {
        "report_underexposure": False,
        "report_overexposure": False,
        "report_brightness": True,
        "report_blurry": True,
    }
    path.write_text(json.dumps(data), encoding="UTF-8")

    reporting = Project.from_path(path).processing_settings.preprocessing.reporting
    assert reporting.blur.reference_threshold == 0.10, reporting.blur.reference_threshold
    print("ancienne forme du bloc        : ok")


def test_no_processing_settings(directory: Path) -> None:
    """Un projet sans bloc de traitement du tout reste valide."""
    project = Project(name="essai")
    path = directory / "nu.spot"
    project.save_as(path)

    assert Project.from_path(path).processing_settings is None
    print("projet sans bloc de traitement: ok")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        test_full_roundtrip(directory)
        test_missing_reporting_block(directory)
        test_previous_reporting_shape(directory)
        test_no_processing_settings(directory)
    print()
    print("toutes les verifications passent")
    sys.exit(0)
