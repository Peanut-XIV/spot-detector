import sys
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Slot
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

        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.accept)

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


if __name__ == "__main__":

    class TestWindow(QMainWindow):
        def __init__(
            self,
            parent: QWidget | None = None,
            flags: Qt.WindowType = Qt.WindowType.Window,
        ) -> None:
            super().__init__(parent, flags)
            self.button = QPushButton("open dialog")
            self.setCentralWidget(self.button)
            self.button.clicked.connect(self.handle_dialog)

        @Slot()
        def handle_dialog(self):
            default_model = ColorAndParams.from_prepopulated_defaults(
                color_name="white"
            )
            dump1 = default_model.model_dump_json()[:]
            dialog = DetectionSettingsDialog(default_model)
            result = dialog.exec()
            if result == QDialog.DialogCode.Rejected:
                print("the user cancelled the current action")
                return
            print("the user updated the detection settings")
            output_model = dialog.model.model_copy(deep=True)
            dump3 = output_model.model_dump_json()[:]

            if dump1 == dump3:
                print("no changes applied")
            else:
                print("changes detected between dump1 and dump3")
                print("dump1:")
                print(dump1)
                print("dump3:")
                print(dump3)

    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
