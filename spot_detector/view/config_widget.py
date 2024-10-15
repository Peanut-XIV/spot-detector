import sys

from PySide6.QtCore import (
    QModelIndex,
    QAbstractItemModel,
    Qt,
    Slot,
)
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from spot_detector.model.models import ColorAndParams
from spot_detector.view.json_tree import JsonModel, TreeItem
from spot_detector.view.parameter_descriptions import InstructionWidget


class ConfigWidget(QWidget):
    def __init__(
            self, 
            parent: QWidget | None = None,
            f: Qt.WindowType = Qt.WindowType.Widget
    ) -> None:
        super().__init__(parent, f)
        layout = QVBoxLayout(self)
        self.model = JsonModel()
        self.infobox_index = 0

        title = QLabel("Settings Panel", self)
        layout.addWidget(title)

        self.splitter = QSplitter(Qt.Orientation.Vertical, self)
        # tree view first
        self.tree_view = ConfigTree(self.model, self)
        self.splitter.addWidget(self.tree_view)
        #then the infoboxes
        self.create_infoboxes()
        self.infobox = self.infoboxes[0]
        self.infobox.setVisible(True)
        self.splitter.setCollapsible(0, False)
        layout.addWidget(self.splitter)


        self.setLayout(layout)

    Slot(QModelIndex)
    def update_infobox(self, index: QModelIndex):
        if not index.isValid():
            print("invalid pointer")
            return

        old_index = self.infobox_index
        self.infobox_index = self.guess_the_field(index)
        # PLACEHOLDER FOR ACTUAL LOGIC
        # index + 1 mod 4
        # if self.infobox_index < 3:
        #     self.infobox_index += 1
        # else:
        #     self.infobox_index = 0
        # ----------------------------
        # Swap visibility
        self.infoboxes[old_index].setVisible(False)
        self.infoboxes[self.infobox_index].setVisible(True)
        self.update()


    def create_infoboxes(self):
        self.infoboxes = [
            InstructionWidget.as_default(self),
            InstructionWidget.as_minimum_distance(self),
            InstructionWidget.as_filter_by_area(self),
            InstructionWidget.as_filter_by_circularity(self),
            InstructionWidget.as_filter_by_convexity(self),
        ]
        for element in self.infoboxes:
            self.splitter.addWidget(element)
            id = self.splitter.indexOf(element)
            self.splitter.setCollapsible(id, False)

    def guess_the_field(self, index: QModelIndex):
        item = index.internalPointer()
        if not isinstance(item, TreeItem):
            print("Not a TreeItem")
            return 0
        value_type = item.value_type
        if isinstance(value_type, str) and item.value == "min_dist":
            return 1
        name = item.key
        children = ["mini", "maxi", "enabled"]
        if name in children:
            parent = item.parent()
            if parent is None:
                return 0
            name = parent.key
        name_list = ["min_dist", "area", "circ", "convex"]
        if name in name_list:
            return name_list.index(name) + 1
        else:
            print("wrong key", name)
            return 0


class ConfigTree(QTreeView):
    def __init__(self, model: QAbstractItemModel | None, parent: ConfigWidget | None = None):
        """ PLEASE NO CYCLIC GRAPHS """
        super().__init__(parent)
        self.setModel(model)
        self.setColumnWidth(0, 175)
        self.setMinimumWidth(300)
        self.setSortingEnabled(True)
        if parent is not None:
            self.clicked.connect(parent.update_infobox)


if __name__ == "__main__":
    app = QApplication()
    json_dump = ColorAndParams.from_prepopulated_defaults("Color").model_dump(mode='python')
    model = JsonModel()
    widget = ConfigWidget()
    widget.model.load(json_dump)
    widget.show()
    sys.exit(app.exec())
