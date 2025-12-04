import sys
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QScrollArea,
    QSplitter,
    QWidget,
)
from PySide6.QtCore import Qt, Slot, Signal

from spot_detector.model.models import ColorAndParams, DetParams
from spot_detector.view.hint_panel import HintPanel
from spot_detector.view.settings_fields import SettingsFields
from spot_detector.view.label_list_widget import LabelWidget


class DetectionSettings(QWidget):
    focused_changed: Signal = Signal(DetParams)
    focused_model_changed: Signal = Signal(DetParams)

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
        self.colors_list = LabelWidget(self.model.det_params, split)
        self.colors_list.setObjectName("Detection_settings_color_list")
        split.addWidget(self.colors_list)

        # Fields
        fields_widget = QScrollArea(self)
        fields_widget.setObjectName("Detection_settings_Fields_container")
        self.fields = SettingsFields(self.model.det_params[0], self)
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
        self.fields.modelChanged.connect(self.colors_list.update_focused_model)
        self.colors_list.focused_changed.connect(self.fields.load)
        self.colors_list.model_list_changed.connect(self.handle_models_change)

    def load(self, model: ColorAndParams):
        self.colors_list.update_models.emit(model.det_params)
        self.fields.load(model.det_params[0])

    @Slot(list)
    def handle_models_change(self, models: list[DetParams]):
        self.model.det_params = models


if __name__ == "__main__":
    settings = ColorAndParams.from_prepopulated_defaults("white")
    settings.append_new_color("orang")
    app = QApplication(sys.argv)
    bidule = DetectionSettings(settings)
    bidule.show()
    sys.exit(app.exec())
