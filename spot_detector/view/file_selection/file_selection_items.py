from _typeshed import SupportsRichComparisonT
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Self, TypeVar

BaseSelf = TypeVar("BaseSelf", bound="BaseItem")

class BaseItem:
    def __init__(self, parent: Self | None) -> None:
        self._parent: Self | None = parent
        self._children: list[Self] = []

    def appendChild(self, child: Self) -> None:
        self._children.append(child)

    def insertChild(self, row: int, child: Self) -> None:
        if 0 <= row < len(self._children):
            self._children.insert(row, child)
        else:
            raise IndexError()

    def removeChild(self, child: Self) -> bool:
        if child in self._children:
            self._children.remove(child)
            return True
        else:
            return False

    def popChild(self, row: int) -> bool:
        if not 0 <= row < len(self._children):
            return False
        else:
            self._children.pop(row)
            return True

    def child(self, row: int) -> Self:
        return self._children[row]

    @property
    def parent(self) -> Self | None:
        return self._parent

    def row(self) -> int:
        if self._parent is None:
            return 0
        else:
            return self._parent._children.index(self)

    def sortChildren(self, key: Callable[[Self], SupportsRichComparisonT]):
        self._children.sort(key=key)

    def childrenCount(self):
        return len(self._children)




class RootItem(BaseItem):
    def __init__(self, headers: list) -> None:
        super().__init__(None)
        self.data = headers




class BaseEntryItem(BaseItem):

    class FileState(Enum):
        Unchecked = -1
        Ok = 0
        NotFound = 1
        BadFormat = 2
        NoAuth = 3

    class Quality(Enum):
        Unchecked = -1
        NoDefect = 0
        Blurry = 1
        OverExposed = 2
        UnderExposed = 4
        RoiFail = 8
        BadFilterShape = 16

    def __init__(self, parent: BaseItem, entry_path: Path) -> None:
        BaseItem.__init__(self, parent)
        self._bad_state_count = 0
        self._quality_warning_count = 0
        self._unchecked_count = 0
        self._file_count = 1

        self._path = entry_path.expanduser()

    @property
    def name(self):
        return self._path.name

    @property
    def parent_directory(self):
        return str(self._path.parent)




class DirectoryEntryItem(BaseEntryItem):
    def __init__(self, parent: BaseItem, entry_path: Path) -> None:
        super().__init__(parent, entry_path)
        pass




class FileEntryItem(BaseEntryItem):
    def __init__(self, parent: DirectoryEntryItem | RootItem, entry_path: Path) -> None:
        super().__init__(parent, entry_path)
