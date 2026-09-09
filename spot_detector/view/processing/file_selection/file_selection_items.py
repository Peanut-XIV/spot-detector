from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Self, TypeAlias

from typing_extensions import override

from spot_detector.misc import canonical_path

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

from enum import Flag, IntEnum
from pathlib import Path


DirFilesPair: TypeAlias = tuple[Path | None, list[Path]]


class GenericStatus(IntEnum):
    Ok = 0
    Unchecked = 1
    Warning = 2
    Error = 3

    def merge(self: Self, other: Self):
        return max(self, other)

    @override
    def __str__(self) -> str:
        match self:
            case self.Ok:
                return "✓"
            case self.Unchecked:
                return "-"
            case self.Warning:
                return "?"
            case self.Error:
                return "!"

    @override
    def __repr__(self) -> str:
        state = ""

        match self:
            case self.Ok:
                state = "Ok"
            case self.Unchecked:
                state = "Unchecked"
            case self.Warning:
                state = "Warning"
            case self.Error:
                state = "Error"

        return f"GenericState:{state}"




class FileStatus(IntEnum):
    Unchecked = -1
    Ok = 0
    NotFound = 1
    BadFormat = 2
    NoAuth = 3

    def to_generic(self) -> GenericStatus:
        match self:
            case self.Unchecked:
                return GenericStatus.Unchecked
            case self.Ok:
                return GenericStatus.Ok
            case self.NotFound | self.BadFormat | self.NoAuth:
                return GenericStatus.Error

    @override
    def __str__(self) -> str:
        match self:
            case self.Unchecked:
                return "Unchecked"
            case self.Ok:
                return "Ok"
            case self.NotFound:
                return "NotFound"
            case self.BadFormat:
                return "BadFormat"
            case self.NoAuth:
                return "NotAuthorized"

    @override
    def __repr__(self) -> str:
        return f"GenericState({str(self)})"


class QualityFlag(Flag):
    Unchecked = 0x00
    Ok = 0x01

    Checked = 0x01
    Blurry = 0x02
    OverExposed = 0x04
    UnderExposed = 0x08
    RoiFail = 0x10
    FilterFailsMatch = 0x20

    def to_generic(self) -> GenericStatus:
        match self:
            case self.Unchecked:
                return GenericStatus.Unchecked
            case self.Checked:
                return GenericStatus.Ok
            case _:
                return GenericStatus.Warning

    @override
    def __repr__(self) -> str:
        if self == self.Unchecked:
            return "Quality(Unchecked)"

        if self == self.Ok:
            return "Quality(Ok)"

        state_string = ""
        first_state = True

        state_bit_name = [
            (self.Checked,  "Checked"),
            (self.Blurry, "Blur"),
            (self.OverExposed, "OverExp"),
            (self.UnderExposed, "UnderExp"),
            (self.RoiFail, "RoiFail"),
            (self.FilterFailsMatch, "BadShape"),
        ]

        for bit, name in state_bit_name:
            if bit & self:
                if first_state:
                    first_state = False
                else:
                    state_string += ", "
                state_string += name

        return f"Quality({state_string})"


    @override
    def __str__(self) -> str:
        if self == self.Unchecked:
            return "Unchecked"

        if self == self.Ok:
            return "No Defect"

        return self.__repr__()


@dataclass
class StatusUpdate:
    file_path: Path
    file_status: FileStatus | None
    quality_status: tuple[QualityFlag, QualityFlag] | None
    error_messages: list[str]


class BaseItem:
    def __init__(self, parent: "RootItem | DirectoryEntryItem | None") -> None:
        self._parent: "RootItem | DirectoryEntryItem | None" = parent
        self._children: list["BaseEntryItem"] = []

    def appendChild(self, child: "BaseEntryItem") -> None:
        self._children.append(child)

    def insertChild(self, row: int, child: "BaseEntryItem") -> None:
        if 0 <= row < len(self._children):
            self._children.insert(row, child)
        else:
            raise IndexError()

    def insertChildren(self, row: int, children: list["BaseEntryItem"]) -> None:
        in_1, in_3 = self._children[:row], self._children[row:]
        self._children = in_1 + children + in_3

    def insertDummyEntries(self, row: int, count: int) -> bool:
        if not (isinstance(self, RootItem) or isinstance(self, DirectoryEntryItem)):
            # Does not support inserting children
            return False

        new_entries = [BaseEntryItem(self, Path()) for _ in range(count)]

        self._children = self._children[:row] + new_entries + self._children[row:]

        return True


    def removeChild(self, child: "BaseEntryItem") -> bool:
        if child in self._children:
            self._children.remove(child)
            return True
        else:
            return False

    def removeChildren(self, row: int, count: int) -> bool:
        if not(0 <= row and row + count - 1 < len(self._children)):
            return False

        in_1 = self._children[:row]
        in_2 = self._children[row+count:]
        self._children = in_1 + in_2

        return True

    def popChild(self, row: int) -> bool:
        if not 0 <= row < len(self._children):
            return False
        else:
            _ = self._children.pop(row)
            return True

    def child(self, row: int) -> "BaseItem":
        return self._children[row]

    @property
    def parent(self) -> "RootItem | DirectoryEntryItem | None":
        return self._parent

    def row(self) -> int:
        if isinstance(self, BaseEntryItem):
            if self._parent is not None:
                return self._parent._children.index(self)
        return 0

    def sortChildren(self, key: Callable[["BaseEntryItem"], "SupportsRichComparison"] | None = None):
        def default_key(item: BaseEntryItem):
            return item.name
        predicate = default_key if key is None else key

        self._children.sort(key=predicate)

    @property
    def childrenCount(self) -> int:
        return len(self._children)

    @property
    def rowCount(self) -> int:
        return len(self._children)


    def get_file_list(self) -> list[Path]:
        files: list[Path] = []
        for child in self._children:
            files += child.get_file_list()
        return files

    def flattened_tree(self) -> list["BaseItem"]:
        items: list["BaseItem"] = [self]
        for child in self._children:
            items += child.flattened_tree()
        return items


    @property
    def file_count(self) -> int:
        return sum(map(lambda x: x.file_count, self._children), start=0)

    def warning_count(self) -> tuple[GenericStatus, int]:
        ok_count = 0
        unchecked_count = 0
        warn_count = 0
        err_count = 0
        for child in self._children:
            match child.generic_status:
                case GenericStatus.Ok:
                    ok_count += 1
                case GenericStatus.Unchecked:
                    unchecked_count += 1
                case GenericStatus.Warning:
                    warn_count += 1
                case GenericStatus.Error:
                    err_count += 1

        match ok_count, unchecked_count, warn_count, err_count:
            case x, 0, 0, 0:
                return (GenericStatus.Ok, x)
            case _, x, 0, 0:
                return (GenericStatus.Unchecked, x)
            case _, _, x, 0:
                return (GenericStatus.Warning, x)
            case _, _, x, y:
                return (GenericStatus.Error, x + y)




class RootItem(BaseItem):
    def __init__(self) -> None:
        super().__init__(None)
        self.data: list[str] = ["Name", "Directory", "Count", "Status"]


    def get_entries_as_pairs(self) -> Sequence[DirFilesPair]:
        pairs: Sequence[DirFilesPair] = []
        singles: list[Path] = []

        for child in self._children:
            match child:
                case DirectoryEntryItem():
                    pairs.append((child.path, child.get_file_list()))
                case FileEntryItem():
                    singles.append(child.path)
                case other:
                    print(f"encountered unexpected dummy item of type '{type(other).__name__}'")

        return pairs + [(None, singles)]



class BaseEntryItem(BaseItem):
    def __init__(self, parent: "RootItem | DirectoryEntryItem", entry_path: Path) -> None:
        BaseItem.__init__(self, parent)
        self._generic_status: GenericStatus = GenericStatus.Unchecked
        self._path: Path = canonical_path(entry_path)

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def parent_directory(self) -> str:
        return str(self._path.parent)

    @property
    def path(self) -> Path:
        return Path(self._path)

    @property
    def generic_status(self) -> GenericStatus:...





class DirectoryEntryItem(BaseEntryItem):
    def __init__(self, parent: RootItem, entry_path: Path) -> None:
        super().__init__(parent, entry_path)
        self._warning_count: int = 0
        self._generic_status: GenericStatus = GenericStatus.Unchecked


    @property
    @override
    def generic_status(self) -> GenericStatus:
        return self._generic_status

    def update_status(self):
        self._generic_status, self._warning_count = super().warning_count()

    @property
    def cached_count(self):
        return self._warning_count

    @override
    def warning_count(self) -> tuple[GenericStatus, int]:
        self.update_status()
        return self._generic_status, self._warning_count

    @override
    def appendChild(self, child: "BaseEntryItem") -> None:
        super().appendChild(child)
        self.update_status()

    @override
    def insertChild(self, row: int, child: "BaseEntryItem") -> None:
        super().insertChild(row, child)
        self.update_status()

    @override
    def insertChildren(self, row: int, children: list["BaseEntryItem"]) -> None:
        super().insertChildren(row, children)
        self.update_status()

    @override
    def insertDummyEntries(self, row: int, count: int) -> bool:
        state = super().insertDummyEntries(row, count)
        self.update_status()
        return state


    @override
    def popChild(self, row: int) -> bool:
        state = super().popChild(row)
        self.update_status()
        return state

    @override
    def removeChild(self, child: "BaseEntryItem") -> bool:
        state = super().removeChild(child)
        self.update_status()
        return state

    @override
    def removeChildren(self, row: int, count: int) -> bool:
        state = super().removeChildren(row, count)
        self.update_status()
        return state


class FileEntryItem(BaseEntryItem):
    def __init__(self, parent: DirectoryEntryItem | RootItem, entry_path: Path) -> None:
        super().__init__(parent, entry_path)
        self._file_status: FileStatus = FileStatus.Unchecked
        self._quality_status: QualityFlag = QualityFlag.Unchecked

    @property
    @override
    def file_count(self) -> int:
        return 1

    @override
    def get_file_list(self) -> list[Path]:
        return [Path(self._path)]

    @property
    @override
    def generic_status(self) -> GenericStatus:
        s1 = self._file_status.to_generic()
        s2 = self._quality_status.to_generic()
        return GenericStatus.merge(s1, s2)

    @property
    def quality_status(self) -> QualityFlag:
        return self._quality_status

    @property
    def file_status(self) -> FileStatus:
        return self._file_status

    @quality_status.setter
    def quality_status(self, status: QualityFlag) -> None:
        self._quality_status = status

    @file_status.setter
    def file_status(self, status: FileStatus) -> None:
        self._file_status = status

    def apply_quality_status(self, mask: QualityFlag, status: QualityFlag) -> None:
        unchanged_bits = self._quality_status & (~mask)
        self._quality_status = unchanged_bits | status


    def apply_status(self, update: StatusUpdate):
        if status := update.file_status:
            self.file_status = status

        if status := update.quality_status:
            mask, value = status
            self.apply_quality_status(mask, value)
