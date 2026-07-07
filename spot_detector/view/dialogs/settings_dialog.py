from enum import Enum
import sys
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Slot, Signal
from spot_detector.view.detection_settings.detection_settings import DetectionSettings
from spot_detector.model.models import ColorAndParams, DetParams


class SettingsWindow(QWidget):

    class ExitStatus(Enum):
        Accepted = 0
        Rejected = 1

    exited: Signal = Signal(ExitStatus)

    def __init__(
        self,
        model: ColorAndParams,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        """
        A dialog for updating and managing detection settings for each label
        class created by the user.
        """
        super().__init__(parent, f)

        self.model = model.model_copy(deep=True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
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
        During init, updates attribute model to have as many settings object as
        there are unique non-zero label classes in ColorData.

        The goal is to add default detection settings for any newly added class.
        """
        # get unique elements
        labels = set([shade.get_label_id() for shade in self.model.shades])
        labels = [label for label in labels if label != 0]
        label_count = len(labels)
        det_variant_count = len(self.model.det_params)
        for label_id in range(det_variant_count, label_count):
            self.model.det_params.append(DetParams.from_prepopulated_defaults(label_id))

    @Slot()
    def reject(self):
        self.close()
        self.exited.emit(self.ExitStatus.Rejected)

    @Slot()
    def accept(self):
        self.close()
        self.exited.emit(self.ExitStatus.Accepted)


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
            self.button.clicked.connect(self.start_dialog)

        @Slot()
        def start_dialog(self):
            default_model = ColorAndParams.from_prepopulated_defaults(
                color_name="white"
            )
            self.dump1 = default_model.model_dump_json()[:]
            self.dialog = SettingsWindow(default_model)
            self.dialog.exited.connect(self.handle_dialog_exit)
            self.dialog.show()

        @Slot(SettingsWindow.ExitStatus)
        def handle_dialog_exit(self, status):
            match status:
                case SettingsWindow.ExitStatus.Rejected:
                    print("the user cancelled the current action")
                    return

                case SettingsWindow.ExitStatus.Accepted:
                    print("the user updated the detection settings")
                    output_model = self.dialog.model.model_copy(deep=True)
                    dump3 = output_model.model_dump_json()[:]

                case _:
                    raise NotImplementedError()

            if self.dump1 == dump3:
                print("no changes applied")
            else:
                print("changes detected between dump1 and dump3")
                print("dump1:")
                print(self.dump1)
                print("dump3:")
                print(dump3)

    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
