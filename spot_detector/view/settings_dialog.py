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
from spot_detector.model.models import ColorAndParams, DetParams


class DetectionSettingsDialog(QDialog):
    def __init__(
        self,
        model: ColorAndParams,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        """
        A dialog for updating and managing detection settings for all the
        labels created by the user.
        """
        super().__init__(parent, f)

        self.model = model.model_copy(deep=True)

        self.prepopulate_detection_settings()

        l1 = QVBoxLayout(self)
        self.settings_widget = DetectionSettings(self.model, self)
        l1.addWidget(self.settings_widget)
        l2 = QHBoxLayout()
        l2.addStretch()
        self.cancel_button = QPushButton(self)
        self.cancel_button.setDefault(True)
        self.cancel_button.setAutoDefault(True)
        self.cancel_button.setText("Cancel")
        l2.addWidget(self.cancel_button)
        self.apply_button = QPushButton(self)
        self.apply_button.setDefault(False)
        self.apply_button.setText("Apply")
        l2.addWidget(self.apply_button)
        l1.addLayout(l2)
        self.setLayout(l1)

        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.accept)
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
        # get unique elements
        labels = set([shade.get_label_id() for shade in self.model.shades])
        labels = [label for label in labels if label != 0]
        label_count = len(labels)
        det_variant_count = len(self.model.det_params)
        for label_id in range(det_variant_count, label_count):
            self.model.det_params.append(DetParams.from_prepopulated_defaults(label_id))

    def on_apply(self):
        # Fetch model
        # store as output data
        # return
        ...


if __name__ == "__main__":
    model = ColorAndParams.from_prepopulated_defaults(color_name="white")
    app = QApplication(sys.argv)
    dialog = DetectionSettingsDialog(model)
    dialog.show()
    sys.exit(app.exec())
