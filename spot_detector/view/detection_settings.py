import sys
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QScrollArea,
    QSplitter,
    QWidget,
)
from PySide6.QtCore import (
    Qt,
)

from spot_detector.model.models import ColorAndParams
from spot_detector.view.hint_panel import HintPanel
from spot_detector.view.settings_fields import SettingsFields


class DetectionSettings(QWidget):
    def __init__(
        self,
        colors,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self.selected_color = 0
        self.selected_hint = 0

        layout = QHBoxLayout(self)
        layout.setObjectName("Detection_settings_layout")
        split = QSplitter(Qt.Orientation.Horizontal, self)

        # Colors
        self.colors_list = QListWidget(split)
        self.colors_list.addItems(colors)
        self.colors_list.setMaximumWidth(200)
        split.addWidget(self.colors_list)

        # Fields
        scroll_area = QScrollArea(self)
        self.fields = SettingsFields(None, self)
        self.fields.setMinimumWidth(300)
        self.fields.setMaximumWidth(300)
        scroll_area.setWidget(self.fields)
        scroll_area.setMinimumWidth(302)
        scroll_area.setMaximumWidth(302)
        split.addWidget(scroll_area)

        # Hint
        scroll_area_2 = QScrollArea(self)
        self.help_panel = HintPanel(self)
        self.help_panel.setMinimumWidth(400)
        scroll_area_2.setWidget(self.help_panel)
        split.addWidget(scroll_area_2)

        layout.addWidget(split)
        self.setLayout(layout)

        self.fields.clicked.connect(self.help_panel.select_hint)

    def load(self, model: ColorAndParams):
        self.colors_list.clear()
        self.colors_list.addItems(model.color_data.names)
        self.fields.load(model.det_params[0])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    bidule = DetectionSettings(["rouge", "vert", "bleu"])
    bidule.show()
    sys.exit(app.exec())
