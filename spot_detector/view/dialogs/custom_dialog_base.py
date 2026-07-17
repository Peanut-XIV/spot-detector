
from enum import Enum

from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import QWidget

class DialogExitStatus(Enum):
    Accepted = 0
    Rejected = 1

class CustomModalDialog(QWidget):
    exited: Signal = Signal(DialogExitStatus)

    def __init__(
        self,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        """
        A dialog for updating and managing detection settings for each label
        class created by the user.
        """
        super().__init__(parent, f)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    @Slot()
    def accept(self):
        _ = self.close()
        self.exited.emit(DialogExitStatus.Accepted)

    @Slot()
    def reject(self):
        _ = self.close()
        self.exited.emit(DialogExitStatus.Rejected)
