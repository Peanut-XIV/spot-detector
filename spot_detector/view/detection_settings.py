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
        model: ColorAndParams,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self.selected_color = 0
        self.selected_hint = 0

        self.model = model

        layout = QHBoxLayout(self)
        layout.setObjectName("Detection_settings_layout")
        split = QSplitter(Qt.Orientation.Horizontal, self)
        split.setObjectName("Detection_settings_splitter")

        # Colors
        # TODO: change to a list that can add and remove entries
        self.colors_list = QListWidget(split)
        self.colors_list.setObjectName("Detection_settings_color_list")
        self.colors_list.addItems(self.model.color_names)
        self.colors_list.setMaximumWidth(200)
        split.addWidget(self.colors_list)

        # Fields
        fields_widget = QScrollArea(self)
        fields_widget.setObjectName("Detection_settings_Fields_container")
        self.fields = SettingsFields(None, self)
        self.fields.setObjectName("Detection_settings_Fields")
        self.fields.setMinimumWidth(300)
        self.fields.setMaximumWidth(300)
        fields_widget.setWidget(self.fields)
        fields_widget.setMinimumWidth(300)
        fields_widget.setMaximumWidth(300)
        split.addWidget(fields_widget)

        # Hint
        help_widget = QScrollArea(self)
        help_widget.setObjectName("scroll_area_2")
        help_widget.setMinimumWidth(400)
        self.help_panel = HintPanel(self, help_widget)
        self.help_panel.setMinimumWidth(400)
        help_widget.setWidget(self.help_panel)
        split.addWidget(help_widget)

        layout.addWidget(split)
        self.setLayout(layout)

        self.fields.clicked.connect(self.help_panel.select_hint)

    def load(self, model: ColorAndParams):
        self.colors_list.clear()
        self.colors_list.addItems(model.color_names)
        self.fields.load(model.det_params[0])


if __name__ == "__main__":
    settings = ColorAndParams.from_prepopulated_defaults("white")
    app = QApplication(sys.argv)
    bidule = DetectionSettings(settings)
    bidule.show()
    sys.exit(app.exec())
