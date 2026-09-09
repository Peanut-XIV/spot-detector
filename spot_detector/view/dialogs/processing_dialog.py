from pathlib import Path
from time import monotonic
import sys
from typing import override

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QCloseEvent

from spot_detector.misc import canonical_path
from spot_detector.model.config_fingerprint import ProcessingSession, create_session, end_session
from spot_detector.model.models import ColorAndParams
from spot_detector.model.processing_settings_models import ProcessingSettingsModel
from spot_detector.model.project import Project
from spot_detector.processing.processing_task_manager import ProcessingTaskManager
from spot_detector.processing.tsv_writer import TSVWriter

from spot_detector.view.dialogs.custom_dialog_base import CustomModalDialog, DialogExitStatus

from spot_detector.view.processing.file_selection.file_selection_panel import FileSelectionPanel
from spot_detector.view.processing.output_panel import OutputFilePanel
from spot_detector.view.processing.settings.processing_settings_panel import ProcessingSettingsPanel


TICK_INTERVAL_MS = 200
CANCEL_GRACE_SECONDS = 10.0


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

        self._session: ProcessingSession | None = None
        self._writer: TSVWriter | None = None
        self._manager: ProcessingTaskManager | None = None
        self._cancel_deadline: float | None = None

        self._timer: QTimer = QTimer(self)
        self._timer.setInterval(TICK_INTERVAL_MS)
        _ = self._timer.timeout.connect(self._on_tick)

        self.setWindowTitle("Processing Dialog")
        self._init_layout()

        _ = self.reject_button.clicked.connect(self.reject)
        _ = self.export_button.clicked.connect(self.on_save_requested)
        _ = self.start_button.clicked.connect(self.on_start_requested)
        _ = self.cancel_button.clicked.connect(self.on_cancel_requested)

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

        self.progress_label: QLabel = QLabel("", self)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        main_layout.addWidget(self.progress_label)

        self.progress_bar: QProgressBar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        buttons_layout = QHBoxLayout()

        self.reject_button: QPushButton = QPushButton("Exit", self)
        buttons_layout.addWidget(self.reject_button)

        buttons_layout.addStretch()

        self.export_button: QPushButton = QPushButton("Export Settings",self)
        buttons_layout.addWidget(self.export_button)

        self.cancel_button: QPushButton = QPushButton("Stop Processing", self)
        self.cancel_button.setVisible(False)
        buttons_layout.addWidget(self.cancel_button)

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
        model_copy = self.project.get_snapshot()
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


    # ------------------------------------------------------------------
    # Processing run
    # ------------------------------------------------------------------

    def _blocking_problems(self, model: ProcessingSettingsModel) -> list[str]:
        """List the reasons the run cannot start, in the user's own terms."""
        problems: list[str] = []

        if not model.entries:
            problems.append("No image has been selected.")

        if not model.output.path:
            problems.append("No output folder has been chosen.")
        elif not Path(model.output.path).is_dir():
            problems.append(f"The output folder does not exist: {model.output.path}")

        dust_filter = model.preprocessing.dust_filter
        if dust_filter.enabled:
            if not dust_filter.path:
                problems.append("The dust filter is enabled but no filter image was chosen.")
            elif not Path(dust_filter.path).is_file():
                problems.append(f"The dust filter image does not exist: {dust_filter.path}")

        return problems

    @Slot()
    def on_start_requested(self) -> None:
        if self._manager is not None:
            return

        model = self.get_model()
        problems = self._blocking_problems(model)
        if problems:
            _ = QMessageBox.warning(
                self,
                "Processing cannot start",
                "\n".join(problems),
            )
            return

        snapshot = self.project.get_snapshot()
        snapshot.set_processing_settings(model)

        dust_filter = model.preprocessing.dust_filter
        filter_path = dust_filter.path if dust_filter.enabled else None

        try:
            session = create_session(snapshot, filter_path)
        except OSError as error:
            _ = QMessageBox.critical(self, "Processing cannot start", str(error))
            return

        try:
            writer = TSVWriter(session)
            writer.prepare_results_file()
            manager = ProcessingTaskManager(session, writer)
            manager.create_task_list()
        except Exception as error:
            session.logger.error(f"setup failed: {error}")
            end_session(session)
            _ = QMessageBox.critical(self, "Processing cannot start", str(error))
            return

        if not manager.task_list:
            session.logger.info("nothing to process, every selected image is already in the table")
            end_session(session)
            _ = QMessageBox.information(
                self,
                "Nothing to process",
                "Every selected image already has a result in this session.",
            )
            return

        manager.init_workers(manager.get_ideal_process_count())
        manager.start_processing()

        self._session = session
        self._writer = writer
        self._manager = manager
        self._cancel_deadline = None

        self.progress_bar.setRange(0, manager.expected)
        self.progress_bar.setValue(0)
        self._set_running(True)
        self._show_progress(0, manager.expected)
        self._timer.start()

    def _set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.export_button.setEnabled(not running)
        self.reject_button.setEnabled(not running)
        self._selection_panel.setEnabled(not running)
        self._settings_panel.setEnabled(not running)
        self._output_panel.setEnabled(not running)

        self.cancel_button.setVisible(running)
        self.cancel_button.setEnabled(running)
        self.progress_bar.setVisible(running)
        self.progress_label.setVisible(running)

    def _show_progress(self, done: int, total: int) -> None:
        self.progress_bar.setValue(done)
        if self._cancel_deadline is None:
            self.progress_label.setText(f"Processing image {done} of {total}")
        else:
            self.progress_label.setText(f"Stopping, {done} of {total} images written")

    @Slot()
    def _on_tick(self) -> None:
        manager = self._manager
        if manager is None:
            self._timer.stop()
            return

        finished = manager.poll()
        self._show_progress(manager.received, manager.expected)

        if not finished and self._cancel_deadline is not None:
            if monotonic() > self._cancel_deadline:
                finished = True

        if finished:
            self._finish_processing()

    @Slot()
    def on_cancel_requested(self) -> None:
        manager = self._manager
        if manager is None or self._cancel_deadline is not None:
            return

        manager.request_cancel()
        self._cancel_deadline = monotonic() + CANCEL_GRACE_SECONDS
        self.cancel_button.setEnabled(False)
        self._show_progress(manager.received, manager.expected)

    def _finish_processing(self) -> None:
        self._timer.stop()

        manager = self._manager
        session = self._session
        if manager is None or session is None:
            self._set_running(False)
            return

        cancelled = self._cancel_deadline is not None
        manager.shutdown()

        written = manager.received
        expected = manager.expected
        directory = session.directory
        end_session(session)

        self._manager = None
        self._writer = None
        self._session = None
        self._cancel_deadline = None
        self._set_running(False)

        if cancelled:
            title = "Processing stopped"
            body = (
                f"{written} of {expected} images were written.\n"
                "Starting again on the same output folder resumes where this run stopped."
            )
        elif written < expected:
            title = "Processing ended with missing results"
            body = (
                f"{written} of {expected} images were written. "
                f"{expected - written} produced no result.\n"
                "See the log for details; starting again processes the missing images."
            )
        else:
            title = "Processing complete"
            body = f"{written} images were processed."

        _ = QMessageBox.information(self, title, f"{body}\n\nResults folder:\n{directory}")

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        if self._manager is None:
            super().closeEvent(event)
            return

        answer = QMessageBox.question(
            self,
            "Processing is running",
            "Stop the current run and close this window?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self.on_cancel_requested()
        event.ignore()



if __name__ == "__main__":
    from PySide6.QtWidgets import QMainWindow, QApplication

    # project: Project = Project(name="default", configuration=ColorAndParams.from_defaults("blaune"))
    project = Project.from_path(canonical_path("~/Desktop/test_run.json"))

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
