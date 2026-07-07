from typing import overload
from typing_extensions import override
from PySide6.QtCore import QAbstractItemModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from spot_detector.view.file_selection.file_selection_items import (
    BaseEntryItem,
    RootItem,
)


class FileSelectionModel(QAbstractItemModel):
    def __init__(self, headers: list) -> None:
        super().__init__()

        self.root_data = headers
        self.root_item = RootItem(headers.copy())

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: Qt.ItemDataRole | int = Qt.ItemDataRole.DisplayRole
    ):
        ...

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole | int = Qt.ItemDataRole.DisplayRole
    ):
        return super().headerData(section, orientation, role)

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> QModelIndex:
        ...

    def add_entry(
        self,
        entry_path: str
    ):
        ...

    def remove_entry(
        self,
        item: BaseEntryItem
    ):
        ...

    def load_entries(self, model) -> None:
        ...

    @override
    @overload
    def parent(self, child: QModelIndex | QPersistentModelIndex | None) -> QModelIndex:
        print("helo")
        return QModelIndex()

    @overload
    def parent(self) -> QObject:
        return QAbstractItemModel.parent(self)
