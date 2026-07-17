from pathlib import Path
import sys

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt, Slot

from spot_detector.model.models import ColorAndParams
from spot_detector.model.processing_settings_models import ProcessingSettingsModel
from spot_detector.model.project import Project
from spot_detector.view.dialogs.custom_dialog_base import CustomModalDialog, DialogExitStatus
from spot_detector.view.file_selection.file_selection_widget import FileSelectionPanel
from spot_detector.view.processing.output_panel import OutputFilePanel
from spot_detector.view.processing.processing_settings_widget import ProcessingSettingsPanel


class ProcessingDialog(CustomModalDialog):

    def __init__(
        self,
        project: Project,
        previous_directory: Path | None = None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window
    ) -> None:
        super().__init__(parent, f)

        self.project: Project = project
        self._previous_directory: Path = previous_directory or Path.home()

        self.setWindowTitle("Processing Dialog")
        self._init_layout()

        _ = self.reject_button.clicked.connect(self.reject)
        _ = self.export_button.clicked.connect(self.on_save_requested)

        _ = self._settings_panel.filter_box.dust_filter_test_requested.connect(self._selection_panel.check_all_files_for_filter_compat)
        _ = self._settings_panel.cropping_box.cropping_test_requested.connect(self._selection_panel.check_selection_for_cropping)



    def _init_layout(self):
        main_layout: QVBoxLayout = QVBoxLayout(self)

        panels_layout = QHBoxLayout()
        panels_layout.setContentsMargins(0,0,0,0)

        self._selection_panel: FileSelectionPanel = FileSelectionPanel(self._previous_directory, self)
        panels_layout.addWidget(self._selection_panel, stretch=1)

        self._settings_panel: ProcessingSettingsPanel = ProcessingSettingsPanel(self._previous_directory, self)
        panels_layout.addWidget(self._settings_panel, stretch=1)

        self._output_panel: OutputFilePanel = OutputFilePanel(self._previous_directory, self)
        panels_layout.addWidget(self._output_panel, stretch=1)

        main_layout.addLayout(panels_layout)
        buttons_layout = QHBoxLayout()

        self.reject_button: QPushButton = QPushButton("Exit", self)
        buttons_layout.addWidget(self.reject_button)

        buttons_layout.addStretch()

        self.export_button: QPushButton = QPushButton("Export Settings",self)
        buttons_layout.addWidget(self.export_button)

        self.start_button: QPushButton = QPushButton("Start Processing", self)
        buttons_layout.addWidget(self.start_button)

        main_layout.addLayout(buttons_layout)


    def get_model(self) -> ProcessingSettingsModel:
        model = ProcessingSettingsModel(
            entries=self._selection_panel.get_model(),
            preprocessing=self._settings_panel.get_model(),
            output=self._output_panel.get_model()
        )
        return model

    @Slot(ProcessingSettingsModel)
    def set_model(self, model: ProcessingSettingsModel) -> None:
        self._selection_panel.set_model(model.entries)
        self._settings_panel.set_model(model.preprocessing)
        self._output_panel.set_model(model.output)

    @Slot()
    def on_save_requested(self) -> None:
        print("save_requested")
        proc_model = self.get_model()
        model_copy = self.project.model_copy(deep=True)
        model_copy.set_processing_settings(proc_model)

        save_dialog = QFileDialog(self, "Save Project", model_copy.latest_save_path or str(Path.home()))
        save_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        save_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)

        res = save_dialog.exec()
        print("exited save dialog")
        if res:
            print("user selected an item")
            selection = save_dialog.selectedFiles()
            if len(selection) != 1:
                print(f"expected 1 item, got {len(selection)}")
                return
            model_copy.save_as(selection[0])
            print("commiting changes to the project object")
            self.project.processing_settings = proc_model
        else:
            print("user selected nothing")
            print("not commiting changes to the project object")


if __name__ == "__main__":
    from PySide6.QtWidgets import QMainWindow, QApplication

    project: Project = Project(name="default", configuration=ColorAndParams.from_defaults("blaune"))

    class TestWindow(QMainWindow):
        def __init__(
            self,
            parent: QWidget | None = None,
            flags: Qt.WindowType = Qt.WindowType.Window,
        ) -> None:
            super().__init__(parent, flags)
            self.button: QPushButton = QPushButton("open dialog")
            self.setCentralWidget(self.button)
            _ = self.button.clicked.connect(self.start_dialog)
            self.dialog: ProcessingDialog = ProcessingDialog(project, Path.home() / "Desktop", self)

        @Slot()
        def start_dialog(self):
            _ = self.dialog.exited.connect(self.handle_dialog_exit)
            self.dialog.show()


        @Slot(DialogExitStatus)
        def handle_dialog_exit(self, status: DialogExitStatus):
            match status:
                case DialogExitStatus.Rejected:
                    print("the user cancelled the current action")
                    return

                case DialogExitStatus.Accepted:
                    print("the user accepted the dialog")


    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()

    sys.exit(app.exec())
