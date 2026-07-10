from collections.abc import Sequence
from typing import TYPE_CHECKING, Callable

from typing_extensions import override

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

from pathlib import Path
from PySide6.QtGui import QColor
from PySide6.QtCore import QAbstractItemModel, QModelIndex, QObject, QPersistentModelIndex, QSize, Qt, Signal, Slot

from spot_detector.view.file_selection.file_selection_items import (
    BaseItem,
    BaseEntryItem,
    DirFilesPair,
    DirectoryEntryItem,
    RootItem,
    FileEntryItem,
    GenericStatus,
    StatusUpdate,
)

class FileSelectionModel(QAbstractItemModel):
    file_count_changed: Signal = Signal(int)
    new_error_messages: Signal = Signal(list)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__()

        self._parent: QObject | None = parent

        self._rootItem: RootItem = RootItem()
        self._rootData: list[str] = self._rootItem.data

        _ = self.rowsInserted.connect(self._refresh_file_count)
        _ = self.rowsRemoved.connect(self._refresh_file_count)
        _ = self.modelReset.connect(self._refresh_file_count)

    @Slot()
    def _refresh_file_count(self):
        count = self.file_count()
        self.file_count_changed.emit(count)

    def resolve_index(self, index: QModelIndex | QPersistentModelIndex | None) -> QModelIndex | QPersistentModelIndex:
        return index or QModelIndex()

    def _item_from_index(self, index: QModelIndex | QPersistentModelIndex) -> BaseItem:
        if not index.isValid():
            return self._rootItem

        item = index.internalPointer()  # pyright: ignore[reportAny]
        match item:
            case BaseItem():
                return item
            case None:
                return self._rootItem
            case other:  # pyright: ignore[reportAny]
                msg = (
                    f"Function argument index {index!r} [row={index.row()}, col={index.column()}]"
                    f" has an internal pointer to an object of type {type(other).__name__} with "  # pyright: ignore[reportAny]
                    f"value {item!r:.100}, was expecting types None or BaseItem"
                )
                raise TypeError(msg)

    def remove_indexes(self, indexes: list[QModelIndex]):
        self.beginResetModel()
        items = [self._item_from_index(idx) for idx in indexes if idx.isValid()]
        entry_items = [item for item in items if isinstance(item, BaseEntryItem)]
        for item in entry_items:
            if parent:=item.parent:
                _ = parent.removeChild(item)
        self.endResetModel()

    @override
    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        base_flag = Qt.ItemFlag.NoItemFlags

        try:
            item = self._item_from_index(index)
        except TypeError:
            return base_flag

        base_flag |= Qt.ItemFlag.ItemIsEnabled

        base_flag |= Qt.ItemFlag.ItemIsSelectable

        match item:
            case FileEntryItem():
                base_flag |= Qt.ItemFlag.ItemNeverHasChildren
            case _:
                pass

        return base_flag


    @override
    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        parent_res = self.resolve_index(parent)
        if parent_res.column() > 0:
            return 0

        parent_item = self._item_from_index(parent_res)
        return parent_item.childrenCount

    @override
    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._rootData)  # 4 : #, Name, Path, Status


    @override
    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: Qt.ItemDataRole | int = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None
        candidate = self._item_from_index(index)
        if isinstance(candidate, BaseEntryItem):
            item: BaseEntryItem = candidate
        else:
            return None

        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            match col:
                case 0:
                    return item.name
                case 1:
                    return item.parent_directory
                case 2:
                    if isinstance(item, DirectoryEntryItem):
                        return item.file_count
                    else:
                        return "-"
                case 3:
                    if isinstance(item, FileEntryItem):
                        return str(item.generic_status)
                    if isinstance(item, DirectoryEntryItem):
                        return str(item.cached_count)
                case _:
                    pass

        if role == Qt.ItemDataRole.ToolTipRole:
            match col:
                case 1:
                    return str(item.path)
                case 3:
                    # TODO: display detailed feedback
                    pass
                case _:
                    pass


        if role == Qt.ItemDataRole.BackgroundRole:
            if col == 3:
                match item.generic_status:
                    case GenericStatus.Unchecked:
                        return QColor("lightGray")
                    case GenericStatus.Ok:
                        return QColor("green")
                    case GenericStatus.Warning:
                        return QColor("orange")
                    case GenericStatus.Error:
                        return QColor("red")

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 2:
                if isinstance(item, FileEntryItem):
                    return QColor("lightGray")
            if col == 3:
                    return QColor("black")

        if role == Qt.ItemDataRole.TextAlignmentRole:
                flag = Qt.AlignmentFlag.AlignVCenter
                flag |= Qt.AlignmentFlag.AlignLeft if col < 2 else Qt.AlignmentFlag.AlignCenter
                return flag
        if role == Qt.ItemDataRole.SizeHintRole:
            sizes: list[QSize] = [
                QSize(100,20),
                QSize(300,20),
                QSize(50,20),
                QSize(50,20),
            ]
            return sizes[col]

        return None

    @override
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole | int = Qt.ItemDataRole.DisplayRole
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._rootData[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                flag = Qt.AlignmentFlag.AlignVCenter
                flag |= Qt.AlignmentFlag.AlignLeft if section < 2 else Qt.AlignmentFlag.AlignCenter
                return flag
            # if role == Qt.ItemDataRole.BackgroundRole:
            #     return QColor("lightGray")
            if role == Qt.ItemDataRole.SizeHintRole:
                return [QSize(100,20), QSize(300,20), QSize(50,20), QSize(50,20)][section]

        return None

    @override
    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> QModelIndex:
        parent_res = self.resolve_index(parent)

        if not self.hasIndex(row, column, parent_res):
            return QModelIndex()

        parent_item = parent_res.internalPointer() if parent_res.isValid() else self._rootItem
        child = parent_item.child(row)
        return self.createIndex(row, column, child)

    @override
    def removeRows(
        self,
        row: int,
        count: int,
        parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> bool:
        parent_res = self.resolve_index(parent)
        parent_item = self._item_from_index(parent_res)

        if not isinstance(parent_item, (RootItem, DirectoryEntryItem)):
            return False

        if row + count > parent_item.childrenCount:
            return False

        self.beginRemoveRows(parent_res, row, row + count - 1)
        success = parent_item.removeChildren(row, count)
        self.endRemoveRows()

        return success


    @override
    def insertRows(
        self,
        row: int,
        count: int,
        parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> bool:
        parent_res = self.resolve_index(parent)
        parent_item = self._item_from_index(parent_res)

        if not isinstance(parent_item, (RootItem, DirectoryEntryItem)):
            return False

        self.beginInsertRows(parent_res, row, row + count - 1)
        success = parent_item.insertDummyEntries(row, count)
        self.endInsertRows()

        return success


    def add_file_entries(
        self,
        entries: list[Path],
        parent: QModelIndex | QPersistentModelIndex | None = None,
    ) -> bool:
        parent_res = self.resolve_index(parent)

        try:
            parent_item = self._item_from_index(parent_res)
        except TypeError:
            return False

        if not isinstance(parent_item, (RootItem, DirectoryEntryItem)):
            return False

        last_row = parent_item.rowCount
        self.beginInsertRows(parent_res, last_row, last_row + len(entries) - 1)

        for entry in entries:
            parent_item.appendChild(FileEntryItem(parent_item, entry))

        self.endInsertRows()

        self.sort_children(parent_res)

        return True

    def add_directory_row(
        self,
        entry: Path,
    ) -> DirectoryEntryItem | None:
        parent_res = QModelIndex()
        parent_item = self._item_from_index(parent_res)
        if not isinstance(parent_item, RootItem):
            print(f"add directory row: root item is not instance of RootItem but of {type(parent_item).__name__}")
            return None

        last_row = parent_item.rowCount

        new_entry = DirectoryEntryItem(parent_item, entry)

        self.beginInsertRows(parent_res, last_row, last_row)
        parent_item.appendChild(new_entry)
        self.endInsertRows()

        self.sort_children(parent_res)

        return new_entry

    def add_directory_and_content(
        self,
        directory: Path,
        content: list[Path],
    ) -> bool:
        dir_entry = self.add_directory_row(directory)

        if dir_entry is None:
            return False

        index = self.index(dir_entry.row(), 0, QModelIndex())

        if not self.add_file_entries(content, index):
            return False
        else:
            return True


    def sort_children(
        self,
        parent: QModelIndex | QPersistentModelIndex,
        key: Callable[[BaseEntryItem],
        "SupportsRichComparison"] | None = None
    ) -> None:
        parent_item = parent.internalPointer() if parent.isValid() else self._rootItem
        if not isinstance(parent_item, (RootItem, DirectoryEntryItem)):
            return

        self.layoutAboutToBeChanged.emit()
        # self.layoutAboutToBeChanged.emit(
        #     [QPersistentModelIndex(parent)],
        #     QAbstractItemModel.LayoutChangeHint.VerticalSortHint,
        # )

        old_indexes = [
            idx for idx in self.persistentIndexList()
            if idx.parent() == parent
        ]
        items = [idx.internalPointer() for idx in old_indexes]

        parent_item.sortChildren(key=key)

        new_indexes: list[QModelIndex] = []
        for idx, item in zip(old_indexes, items):  # pyright: ignore[reportAny]
            index = self.createIndex(item.row(), idx.column(), item)  # pyright: ignore[reportAny]
            new_indexes.append(index)

        self.changePersistentIndexList(old_indexes, new_indexes)

        self.layoutChanged.emit()
        # self.layoutChanged.emit()
        #     [QPersistentModelIndex(parent)],
        #     QAbstractItemModel.LayoutChangeHint.VerticalSortHint,
        # )


    def load_entries(self, files: list[Path]) -> None:

        root = RootItem()

        for file in files:
            entry = FileEntryItem(root, file)
            root.appendChild(entry)

        self.beginResetModel()
        self._rootItem = root
        self.endResetModel()


    def load_entries_from_pairs(self, pairs: Sequence[DirFilesPair]) -> None:
        root = RootItem()

        for dir_path, file_paths in pairs:
            if dir_path is None:
                container = root
            else:
                container = DirectoryEntryItem(root, dir_path)
                root.appendChild(container)

            for file_path in file_paths:
                container.appendChild(FileEntryItem(container, file_path))

        for entry in root._children:  # pyright: ignore[reportPrivateUsage]
            if isinstance(entry, DirectoryEntryItem):
                entry.sortChildren()

        root.sortChildren()

        self.beginResetModel()
        self._rootItem = root
        self.endResetModel()


    def get_entries_as_pairs(self) -> Sequence[DirFilesPair]:
        return self._rootItem.get_entries_as_pairs()

    def get_file_list(self) -> list[Path]:
        return self._rootItem.get_file_list()

    @override
    def parent(self, child: QModelIndex | QPersistentModelIndex) -> QModelIndex:  # pyright: ignore[reportIncompatibleMethodOverride]
        if not child.isValid():
            return QModelIndex()
        child_item = child.internalPointer()  # pyright: ignore[reportAny]
        if not isinstance(child_item, BaseItem):
            return QModelIndex()
        parent_item = child_item.parent
        if parent_item is None or parent_item is self._rootItem:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def file_count(self):
        return self._rootItem.file_count

    def update_dir_status(self, index: QModelIndex):
        item = self._item_from_index(index)
        if not isinstance(item, DirectoryEntryItem):
            return

        item.update_status()

        row = index.row()
        parent_index = index.parent()
        from_cell = self.index(row, 0, parent_index)
        to_cell = self.index(row, 4, parent_index)
        roles = [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole]

        self.dataChanged.emit(from_cell, to_cell, roles)

    def check_entry(self, index: QModelIndex, check_function: Callable[[Path], StatusUpdate]):
        """
        index must point to a FileEntryItem instance, otherwise does nothing
        """
        item = self._item_from_index(index)
        if not isinstance(item, FileEntryItem):
            return

        result = check_function(item.path)

        self.new_error_messages.emit(result.error_messages)

        if status := result.file_status:
            item.file_status = status

        if status := result.quality_status:
            mask, value = status
            item.apply_quality_status(mask, value)

        row = index.row()
        parent_index = index.parent()
        from_cell = self.index(row, 0, parent_index)
        to_cell = self.index(row, 4, parent_index)
        roles = [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole]

        self.dataChanged.emit(from_cell, to_cell, roles)

        parent_item = item.parent
        if not isinstance(parent_item, DirectoryEntryItem):
            return

        self.update_dir_status(parent_index)

    def check_entries(self, entries: list[QModelIndex], check_function: Callable[[Path], StatusUpdate]):
        """
        Applies a check function on a set of items designated by their QModelIndexes,
        then reports the check status to them.
        """
        items = [self._item_from_index(idx) for idx in entries]
        file_items = [it for it in items if isinstance(it, FileEntryItem)]
        parent_items = [it.parent for it in file_items]
        dir_items = [ it for it in parent_items if isinstance(it, DirectoryEntryItem)]

        for item in file_items:
            update = check_function(item.path)
            item.apply_status(update)
            self.new_error_messages.emit(update.error_messages)

            if parent_item := item.parent:
                parent_index = self.index(parent_item.row(), 0, QModelIndex())
            else:
                parent_index = QModelIndex()

            cell = self.index(item.row(), 3, parent_index)
            roles = [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole]
            self.dataChanged.emit(cell, cell, roles)

        for item in dir_items:
            item.update_status()
            cell = self.index(item.row(), 3, QModelIndex())
            roles = [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole]
            self.dataChanged.emit(cell, cell, roles)

    def check_all(self, check_function: Callable[[Path], StatusUpdate]):
        items = self._rootItem.flattened_tree()

        file_items = [item for item in items if isinstance(item, FileEntryItem)]
        dir_items = [item for item in items if isinstance(item, DirectoryEntryItem)]

        self.beginResetModel()

        for item in file_items:
            fp = item.path
            update = check_function(fp)
            item.apply_status(update)
            self.new_error_messages.emit(update.error_messages)

        for item in dir_items:
            item.update_status()

        self.endResetModel()


