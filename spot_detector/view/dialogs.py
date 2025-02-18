from PySide6.QtWidgets import (
    QWidget,
    QFileDialog,
)
from PySide6.QtCore import (
    Qt,
    Slot,
)
from spot_detector.file_utils import VALID_IMAGE_MIME_TYPES


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
