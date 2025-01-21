from PySide6.QtCore import (
    Qt,
    QObject,
    QThread,
)


class WorkerThread(QThread):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
