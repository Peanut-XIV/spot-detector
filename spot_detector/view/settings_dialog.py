import sys
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from spot_detector.model.project import Project
from spot_detector.view.detection_settings import DetectionSettings
from spot_detector.model.models import ColorAndParams


class DetectionSettingsDialog(QDialog):
    def __init__(
        self,
        config: ColorAndParams,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        """
        A dialog for updating and managing detection settings for all the
        labels created by the user.
        """
        super().__init__(parent, f)

        self.config_copy = config.model_copy(deep=True)

        self.prepopulate_detection_settings()

        self.settings = settings.model_copy(deep=True)
        self.setModal(True)

        l1 = QVBoxLayout(self)
        self.settings_widget = DetectionSettings(settings, self)
        l1.addWidget(self.settings_widget)

        l2 = QHBoxLayout(self)
        l2.addStretch()
        self.cancel_button = QPushButton(self)
        self.cancel_button.setText("Cancel")
        l2.addWidget(self.cancel_button)
        self.apply_button = QPushButton(self)
        self.apply_button.setText("Apply")
        l2.addWidget(self.apply_button)

        l1.addLayout(l2)

        self.setLayout(l1)
        # Add main widget
        # unmap enter
        # add signals -> get / set config
        # add save button
        # add return button
        # link close button to msgbox

    def prepopulate_detection_settings(self):
        """
        During init, updates config_copy to have as many detection settings
        as there are unique non-zero labels in ColorData.

        The goal is to add default detection settings for any new label.
        """
        # TODO: write method
        ...


if __name__ == "__main__":
    settings = ColorAndParams.from_prepopulated_defaults(color_name="white")
    app = QApplication(sys.argv)
    dialog = DetectionSettingsDialog(settings)
    dialog.show()
    sys.exit(app.exec())
