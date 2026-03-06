from pathlib import Path
import sys
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QKeyEvent
from spot_detector.model import image_set_model
from spot_detector.model.image_set_model import ImageEntry, ImageSetModel
from spot_detector.model.project import Project
from spot_detector.view.path_line_widget import PathLineWidget


class ImageProcessingDialog(QDialog):
    """
    The dialog Window that appears when the user wishes to process a set of pictures
    """

    spacer_size = 5

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        """Constructor of the ImageProcessingDialogue object

        This should only be called once a proper detection settings model is made.
        Checking the existence of a valid set of detection settings is left to the caller.
        """
        super().__init__(parent, f)
        self.setWindowTitle("Start Processing")

        self.project_copy = project.model_copy(deep=True)
        self.user_starts_processing = False
        self.saved_config = None

        base_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()

        # UI divided in 3 columns
        file_selection_layout = self._create_file_selection_layout(None)
        content_layout.addLayout(file_selection_layout)
        content_layout.addWidget(self.make_vline())
        dust_filter_layout = self._create_dust_filter_layout()
        content_layout.addLayout(dust_filter_layout)
        content_layout.addWidget(self.make_vline())
        output_path_layout = self._create_output_path_layout()
        content_layout.addLayout(output_path_layout)
        base_layout.addLayout(content_layout)

        # Finally buttons to cancel or continue
        accept_reject_layout = self._create_accept_reject_layout()
        base_layout.addLayout(accept_reject_layout)

        self.add_files_button.clicked.connect(self.add_files_dialog)
        self.cancel_button.clicked.connect(self.exit_without_saving)
        self.save_and_exit_button.clicked.connect(self.save_and_exit)
        self.save_and_start_button.clicked.connect(self.save_and_start)

        self.accepted.connect(self.save_config)
        self.rejected.connect(self.null_config)

    def _create_file_selection_layout(
        self, file_entries: list[ImageEntry] | None
    ) -> QVBoxLayout:
        """Creates the first UI column and returns it as a layout

        Initialises `self.file_list`, `self.element_counter`, `self.error_box`

        Returns
        -------
        QVBoxLayout() The created layout containing different widgets
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Input Files"))
        # layout.addStretch()
        self._image_set_model = ImageSetModel(file_entries)
        self.file_tree = self._create_image_set_view(self._image_set_model)
        layout.addWidget(self.file_tree)
        self.add_files_button = QPushButton("Add Files")
        layout.addWidget(self.add_files_button)
        self.element_counter = QLabel("Total files: 0")
        layout.addWidget(self.element_counter)
        self.error_box = QLabel("")
        self.error_box.setFrameShape(QFrame.Shape.Panel)
        self.error_box.setFrameShadow(QFrame.Shadow.Sunken)
        self.error_box.setWordWrap(False)
        layout.addWidget(self.error_box)
        layout.addStretch()
        return layout

    def _create_image_set_view(self, model: ImageSetModel | None) -> QTableView:
        view = QTableView()

        view.setSortingEnabled(False)
        view.setAcceptDrops(False)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        view.horizontalHeader().setStretchLastSection(True)
        view.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        if model is not None:
            view.setModel(model)
            view.resizeColumnToContents(0)

        return view

    def _create_dust_filter_layout(self) -> QVBoxLayout:
        """Creates the second UI column and returns it as a layout

        Initialises `self.dust_filter_checkbox` and `self.dust_filter_pathline`

        Returns
        -------
        QVBoxLayout()
            The created layout containing different widgets
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Choose dust filter"))
        # layout.addStretch()
        self.dust_filter_checkbox = QCheckBox()
        self.dust_filter_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.dust_filter_checkbox.setText("Enable dust filter")
        layout.addWidget(self.dust_filter_checkbox)
        path_layout = QHBoxLayout()
        self.dust_filter_pathline = PathLineWidget(
            "read_only_img", "Dust filter path...", None, None
        )
        path_layout.addWidget(self.dust_filter_pathline)
        path_layout.addWidget(self.dust_filter_pathline.get_button())
        layout.addLayout(path_layout)
        note = QLabel(
            "Note: if the dust filter is used, all provided files must"
            " come from the same camera and have the same dimensions."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.df_check_dimensions_button = QPushButton("Check dimensions")
        layout.addWidget(self.df_check_dimensions_button)
        layout.addStretch()

        self.dust_filter_checkbox.checkStateChanged.connect(
            self.on_dust_filter_check_state_change
        )
        self.on_dust_filter_check_state_change(self.dust_filter_checkbox.checkState())
        self.df_check_dimensions_button.clicked.connect(
            self.dust_filter_check_dimensions
        )
        return layout

    @Slot(Qt.CheckState)
    def on_dust_filter_check_state_change(self, new_state: Qt.CheckState):
        self.dust_filter_pathline.setEnabled(new_state == Qt.CheckState.Checked)
        self.dust_filter_pathline.explore_button.setEnabled(
            new_state == Qt.CheckState.Checked
        )

    @Slot()
    def dust_filter_check_dimensions(self):
        entries = self._image_set_model._entries[:]
        filter = self.project_copy.dust_filter_image_path

        if filter is None:
            ...  # handle this code path
            return

        ref_width, ref_height = get_img_size(filter)

        for img in images:
            width, height = get_img_size(img)

    def _create_output_path_layout(self) -> QVBoxLayout:
        """Creates the Third UI column and returns it as a layout

        initialises `self.output_pathline` and `self.resume_postcrash_checkbox`

        Returns
        -------
        QVBoxLayout()
            The created layout containing different widgets
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select output file path"))
        # layout.addStretch()
        sub_layout = QHBoxLayout()

        self.output_pathline = PathLineWidget(
            "other", "Output file path...", None, None
        )
        sub_layout.addWidget(self.output_pathline)
        sub_layout.addWidget(self.output_pathline.get_button())
        layout.addLayout(sub_layout)
        self.resume_postcrash_checkbox = QCheckBox()
        self.resume_postcrash_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.resume_postcrash_checkbox.setText("Resume after crash")
        layout.addWidget(self.resume_postcrash_checkbox)
        note = QLabel(
            "If this option is selected and the given output file already "
            "exists, ignores files that were already processed and appends "
            "data about the remaining ones."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return layout

    def _create_accept_reject_layout(self) -> QHBoxLayout:
        """Creates the bottom line of the UI and returns it as a UI

        initialises `self.cancel_button`, `self.save_and_exit_button` and `self.save_and_start_button`

        Returns
        -------
        QHBoxLayout()
            The created layout containing different widgets
        """
        layout = QHBoxLayout()
        self.cancel_button = QPushButton("Exit")
        layout.addWidget(self.cancel_button)
        layout.addStretch()
        self.save_and_exit_button = QPushButton("Save and Exit")
        layout.addWidget(self.save_and_exit_button)
        self.save_and_start_button = QPushButton("Save and Start Processing")
        self.save_and_start_button.setDefault(True)
        layout.addWidget(self.save_and_start_button)
        return layout

    @Slot()
    def add_files_dialog(self):
        dialog = QFileDialog()
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        if dialog.exec():
            self.add_paths(dialog.selectedFiles())

    def add_paths(self, paths: list[str]):
        for fpath in paths:
            fpath = Path(fpath)

            if fpath.is_file():
                self.add_file(fpath)

            else:
                print("unexpected path object:", fpath)
        self.update_file_count()

    def update_file_count(self):
        filecount = self.file_tree.topLevelItemCount()
        self.element_counter.setText(f"Total files: {filecount}")

    def add_file(self, new_file: Path):
        exp_path = str(new_file.expanduser())
        # This kind of match may fail if hardlinks are used...
        matches = self.file_tree.findItems(exp_path, Qt.MatchFlag.MatchExactly, 1)
        if len(matches) > 0:
            return

        new_entry = QTreeWidgetItem(self.file_tree)
        new_entry.setData(0, Qt.ItemDataRole.DisplayRole, new_file.name)
        new_entry.setData(1, Qt.ItemDataRole.DisplayRole, exp_path)

    @staticmethod
    def make_vline() -> QFrame:
        """Makes a vertical separator widget

        Returns
        -------
        QFrame
            A QFrame with shape type `VLine`,
            shadow type `Plain` and line width 0.
        """
        sep = QFrame()
        sep.setFrameStyle(QFrame.Shadow.Plain | QFrame.Shape.VLine)
        sep.setLineWidth(0)
        return sep

    @Slot()
    def exit_without_saving(self):
        self.user_starts_processing = False
        self.reject()

    @Slot()
    def save_and_exit(self):
        self.user_starts_processing = False
        self.accept()

    @Slot()
    def save_and_start(self):
        self.user_starts_processing = True
        self.accept()

    @Slot()
    def save_config(self):
        print("saving config (to be implemented)")
        # TODO: implement config saving

    @Slot()
    def null_config(self):
        print("nulling config")
        self.saved_config = None

    def keyPressEvent(self, arg__1: QKeyEvent):
        key = arg__1.key()
        if key == Qt.Key.Key_Delete:
            self.remove_selected_files()

    def remove_selected_files(self):
        selection = self.file_tree.selectedItems()
        for item in selection:
            index = self.file_tree.indexOfTopLevelItem(item)
            print(f"removing item at index {index}")
            _ = self.file_tree.takeTopLevelItem(index)
        self.update_file_count()

    def get_images_to_process(self):
        for item_idx in range(self.file_tree.topLevelItemCount()):
            print(item_idx)
        return [str(i) for i in range(21)]


if __name__ == "__main__":
    project = Project(name="some_project")
    app = QApplication(sys.argv)
    diag = ImageProcessingDialog(project)
    diag.show()
    sys.exit(app.exec())
