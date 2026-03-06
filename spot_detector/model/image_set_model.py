from typing import Any
from PySide6.QtCore import (
    QObject,
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
)
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView
from pydantic import BaseModel, Field
import sys


class ImageEntry(BaseModel):
    name: str = Field(default="")
    full_path: str = Field(default="")


class ImageSetModel(QAbstractTableModel):
    """An implementation of an ItemModel for interacting with a set of
    FileEntries containing a name and a fully expanded path (both strings).
    """

    base_column_count = 2

    def __init__(
        self,
        entries: list[ImageEntry] | None = None,
        parent: QObject | None = None,
    ) -> None:

        super().__init__(parent)
        if entries is not None:
            self._entries = [im.model_copy(deep=True) for im in entries]
        else:
            self._entries = []
        self._header = ["Image Name", "Full path"]

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self._header)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        supported_roles = [
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ]
        if role not in supported_roles:
            return None
        if not self.index_is_actually_valid(index):
            return None

        if index.column() == 0:
            return self._entries[index.row()].name
        elif index.column() == 1:
            return self._entries[index.row()].full_path
        else:
            return None

    def index_is_actually_valid(
        self,
        index: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        validity = (
            index.isValid()
            and index.column() < self.columnCount()
            and index.row() < self.rowCount()
        )
        return validity

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole:
            return False

        if not self.index_is_actually_valid(index):
            return False

        if not isinstance(value, str):
            return False

        if index.column() == 0:
            self._entries[index.row()].name = value
            self.dataChanged.emit(index, index, [role])
            return True

        elif index.column() == 1:
            self._entries[index.row()].full_path = value
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(
        self,
        index: QModelIndex | QPersistentModelIndex,
    ) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled

        if not self.index_is_actually_valid(index):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        return (
            super().flags(index)
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsSelectable
        )

    def insertRows(
        self,
        row: int,
        count: int,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> bool:
        if row > self.rowCount():
            return False

        self.beginInsertRows(parent, row, row + count - 1)
        in_before = self._entries[:row]
        in_after = self._entries[row:]
        self._entries = in_before + [ImageEntry() for _ in range(count)] + in_after
        self.endInsertRows()
        return True

    def removeRows(
        self,
        row: int,
        count: int,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> bool:
        """Custom Implementation of the RemoveRows method

        If count + row - 1 goes beyond the bounds of the data,
        the function doesn't remove content and returns False.
        """
        if row + count - 1 >= len(self._entries):
            return False

        # Should not fail now
        self.beginRemoveRows(parent, row, row + count - 1)
        # _entries = [..., r-1, r, r+1, ..., r+c-1, r+c, r+c+1, ...]
        #            <--in_1--> <-----Remove------> <-----in_2----->
        in_1 = self._entries[:row]
        in_2 = self._entries[row + count :]
        self._entries = in_1 + in_2
        self.endRemoveRows()
        return True

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:

        supported_roles = [
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ]

        if role not in supported_roles:
            return None

        if orientation == Qt.Orientation.Vertical:
            if section < self.rowCount():
                return f"row {section}"
            else:
                return None

        if section < self.columnCount():
            return self._header[section]

        else:
            return None


if __name__ == "__main__":
    files_and_paths = [
        ("file_1.txt", "path/to/a/file_1.txt"),
        ("file_2.txt", "path/to/a/file_2.txt"),
        ("file_3.txt", "path/to/a/file_3.txt"),
        ("file_4.txt", "path/to/a/file_4.txt"),
        ("file_5.txt", "path/to/a/file_5.txt"),
        ("file_6.txt", "path/to/a/file_6.txt"),
    ]
    entries = [ImageEntry(name=n, full_path=fp) for n, fp in files_and_paths]

    app = QApplication(sys.argv)
    window = QMainWindow()
    model = ImageSetModel(entries)

    view = QTableView()
    view.setModel(model)
    view.setSortingEnabled(False)
    view.setAcceptDrops(False)
    view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    view.horizontalHeader().setStretchLastSection(True)
    view.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
    view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

    window.setCentralWidget(view)
    window.show()
    sys.exit(app.exec())
