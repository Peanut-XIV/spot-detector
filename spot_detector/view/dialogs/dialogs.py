from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
    QWidget,
    QDialog,
    QLabel,
)
from PySide6.QtCore import Qt
from spot_detector.file_utils import (
    VALID_IMAGE_MIME_TYPES,
    VALID_CSV_MIME_TYPES,
)


class ReadOnlyImageFileDialog(QFileDialog):
    """
    A QFileDialog taylored to look for a single read-only image that
    OpenCV-Python can open. Used for the reference image used for setting the
    spot detection parameters and for the dust filter to use on every image. If
    filter is untouched or set to "", a set of generally compatible image file
    MIME types is chosen.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        caption: str = "",
        directory: str = "",
        filter: str = "",
    ):
        super().__init__(parent, caption, directory, filter)
        if filter == "":
            self.setMimeTypeFilters(VALID_IMAGE_MIME_TYPES)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)


class OpenDirFileDialog(QFileDialog):
    """
    A QFileDialog made to open a directory in read-only.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        caption: str = "",
        directory: str = "",
    ):
        super().__init__(parent, caption, directory)
        self.setFileMode(QFileDialog.FileMode.Directory)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)


class OpenProcessingFileDialog(QFileDialog):
    """
    A dialog made to open a csv file that could be written to.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        caption: str = "",
        directory: str = "",
        filter: str = "",
    ):
        super().__init__(parent, caption, directory, filter)
        if len(filter) == 0:
            self.setMimeTypeFilters(VALID_CSV_MIME_TYPES)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)


class OpenProjectDialog(QFileDialog):
    """
    A File dialog for opening an existing project
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        caption: str = "Open an existing project",
        directory: str = "~/Desktop/",
    ):
        super().__init__(parent, caption, directory)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self.setNameFilter("Project File (*.spot *.json)")


class SaveProjectAsDialog(QFileDialog):
    """
    A File Dialog to set the project's save path and save it there.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        caption: str = "Save current project as:",
        directory: str = "",
    ):
        super().__init__(parent, caption, directory)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setDefaultSuffix("spot")


class ConfirmOverwriteDialog(QDialog):
    def __init__(
        self,
        path,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, f)
        layout = QVBoxLayout(self)
        text = QLabel(
            f"{str(path)} already exists. Do you wish to overwrite this file?"
        )
        buttons = QHBoxLayout(self)
        cancel = QPushButton("Cancel", self)
        overwrite = QPushButton("Overwrite", self)
        buttons.addWidget(cancel)
        buttons.addWidget(overwrite)
        layout.addWidget(text)
        layout.addLayout(layout)
        cancel.clicked.connect(self.reject)
        overwrite.clicked.connect(self.accept)


class LoadPaletteDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, f)

        self.load_current_palette: bool = False

        prompt = QLabel(
            "Do you wish to apply the current palette on this reference image?\n"
            "\nYou can instead generate a new palette from the reference image."
        )
        yes = QPushButton("Yes, apply.")
        no = QPushButton("No, generate a new palette.")
        cancel = QPushButton("cancel")

        l1 = QVBoxLayout()
        l1.addWidget(prompt)

        l2 = QHBoxLayout()
        l2.addWidget(yes)
        l2.addWidget(no)
        l2.addWidget(cancel)

        l1.addLayout(l2)

        self.setLayout(l1)

        yes.clicked.connect(self.on_click_yes)
        no.clicked.connect(self.on_click_no)
        cancel.clicked.connect(self.reject)

    def on_click_yes(self):
        self.load_current_palette = True
        self.accept()

    def on_click_no(self):
        self.load_current_palette = False
        self.accept()


