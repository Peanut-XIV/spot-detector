from typing_extensions import override
from random import randint

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QGroupBox,
    QDoubleSpinBox,
    QLineEdit,
)

from PySide6.QtGui import (
    QMouseEvent,
)

from PySide6.QtCore import (
    Signal,
    Slot,
    Qt,
)

from spot_detector.model.models import DetParams, SimpleParam
from spot_detector.view.detection_settings.hint_panel import Hint


class SettingsFields(QWidget):
    clicked: Signal = Signal(Hint)
    modelChanged: Signal = Signal(DetParams)

    def __init__(
        self,
        model: DetParams | None,
        parent: QWidget | None = None,
        f: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, f)
        self.setObjectName("Settings_Fields")

        if model is None:
            self.model: DetParams = DetParams.from_defaults(f"unnamed_color_{randint(0, 65535)}")
        else:
            self.model = model.model_copy(deep=True)

        layout = QVBoxLayout(self)
        layout.setObjectName("Settings_Fields_layout")

        self.name_field:      NameField = NameField(self.model.color_name, self)  # TODO: Handle Hint
        self.min_dist:     MinDistField = MinDistField(self.model.min_dist, self)  # TODO: Handle Hint
        self.area:    SimpleParamWidget = SimpleParamWidget("Filter by Area", Hint.AREA, self.model.area, 4000, 1, self)
        self.convex:  SimpleParamWidget = SimpleParamWidget("Filter by Convexity", Hint.CONV, self.model.convex, 1, 0.05, self)
        self.circ:    SimpleParamWidget = SimpleParamWidget("Filter by Circularity", Hint.CIRC, self.model.circ, 1, 0.05, self)

        layout.addWidget(self.name_field)
        layout.addWidget(self.min_dist)
        layout.addWidget(self.area)
        layout.addWidget(self.convex)
        layout.addWidget(self.circ)

        layout.addStretch(1)

        self.setLayout(layout)

        _ = self.name_field.valueChanged.connect(self.change_color_name)
        _ = self.min_dist.valueChanged.connect(self.change_min_dist)
        _ = self.area.modelChanged.connect(self.emit_new_model)
        _ = self.convex.modelChanged.connect(self.emit_new_model)
        _ = self.circ.modelChanged.connect(self.emit_new_model)

    @Slot(str)
    def change_color_name(self, name: str):
        self.model.color_name = name
        self.emit_new_model()

    @Slot(str)
    def change_min_dist(self, dist: float):
        self.model.min_dist = dist
        self.emit_new_model()

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # print("Click BG")
            self.clicked.emit(Hint.DEFAULT)
        else:
            super().mousePressEvent(event)

    @Slot(DetParams)
    def load(self, model: DetParams):
        # print("Settings Fields: loading model")
        self.name_field.field.setText(model.color_name)
        self.min_dist.spinbox.setValue(model.min_dist or 0)
        self.area.load(model.area)
        self.convex.load(model.convex)
        self.circ.load(model.circ)

    @Slot()
    def emit_new_model(self):
        """
        Upon update, children widgets emit a signal that get caught by this
        function. Then a different signal is emited containing a copy of the
        new model.
        """
        # print("emiting updated model")
        self.modelChanged.emit(self.model.model_copy(deep=True))


class SimpleParamWidget(QGroupBox):
    modelChanged: Signal = Signal()

    def __init__(
        self,
        name: str,
        hint_id: Hint,
        model: SimpleParam,
        maximum: float | None,
        step: float = 1,
        parent: QWidget | None = None,
    ) -> None:
        """
        A Widget representing a SimpleParam from models.py
        Spinboxes get values between 0 and maximum (must be positive)
        """
        super().__init__(name, parent)
        self.setObjectName("Simple_param_widget_" + name)

        self.model: SimpleParam = model

        self.hint_id: Hint = hint_id

        # Main Parameter Enabled checkbox
        layout = QVBoxLayout(self)
        layout.setObjectName("Simple_Param_layout")
        self.enabled_checkbox: QCheckBox = QCheckBox("Enabled", self)
        check_state = bool2CheckState(self.model.enabled)
        self.enabled_checkbox.setCheckState(check_state)
        layout.addWidget(self.enabled_checkbox)

        mini_layout = QHBoxLayout()
        mini_layout.addWidget(QLabel("Minimum", self))
        self.mini_spinbox: QDoubleSpinBox = QDoubleSpinBox(self)
        self.mini_spinbox.setMinimum(0)
        # setting maximum with priority for the model
        if self.model.maxi is not None:
            self.mini_spinbox.setMaximum(self.model.maxi)
        elif maximum is not None:
            self.mini_spinbox.setMaximum(maximum)
        self.mini_spinbox.setValue(self.model.mini)
        self.mini_spinbox.setSingleStep(step)
        self.mini_spinbox.setEnabled(self.model.enabled)
        mini_layout.addWidget(self.mini_spinbox)
        layout.addLayout(mini_layout)

        maxi_layout = QHBoxLayout()
        self.maxi_enabled_checkbox: QCheckBox = QCheckBox("Maximum", self)
        check_state = bool2CheckState(self.model.maxi is not None)
        self.maxi_enabled_checkbox.setCheckState(check_state)
        maxi_layout.addWidget(self.maxi_enabled_checkbox)
        self.maxi_spinbox: QDoubleSpinBox = QDoubleSpinBox(self)
        self.maxi_spinbox.setMinimum(self.model.mini)
        maxi_value = self.model.maxi or maximum or self.model.mini
        self.maxi_spinbox.setValue(maxi_value)
        if maximum is not None:
            self.maxi_spinbox.setMaximum(maximum)
        self.maxi_spinbox.setSingleStep(step)
        enabled = self.model.enabled and (self.model.maxi is not None)
        self.maxi_spinbox.setEnabled(enabled)
        maxi_layout.addWidget(self.maxi_spinbox)
        layout.addLayout(maxi_layout)

        self.setLayout(layout)

        # Connect signals
        # Allows for smart behavior without needing the control layer
        _ = self.mini_spinbox.valueChanged.connect(self.on_mini_changed)
        _ = self.maxi_spinbox.valueChanged.connect(self.on_maxi_changed)
        _ = self.enabled_checkbox.checkStateChanged.connect(self.on_enabled_changed)
        _ = self.maxi_enabled_checkbox.checkStateChanged.connect(
            self.on_maxi_enabled_changed
        )

    @Slot(float)
    def on_maxi_changed(self, value: float):
        """
        updates the model then send emits a "modelChanged" signal
        """
        # print("maximum changed")
        self.mini_spinbox.setMaximum(value)
        self.model.maxi = value
        self.modelChanged.emit()

    @Slot(float)
    def on_mini_changed(self, value: float):
        """
        updates the model then send emits a "modelChanged" signal
        """
        # print("minimum changed")
        self.maxi_spinbox.setMinimum(value)
        self.model.mini = value
        self.modelChanged.emit()

    @Slot(Qt.CheckState)
    def on_enabled_changed(self, state: Qt.CheckState):
        """
        updates the model then send emits a "modelChanged" signal
        """
        # print("enabled state changed")
        enabled = checkState2Bool(state)
        maxi_enabled = checkState2Bool(self.maxi_enabled_checkbox.checkState())
        self.mini_spinbox.setEnabled(enabled)
        self.maxi_spinbox.setEnabled(enabled and maxi_enabled)
        self.model.enabled = enabled
        self.modelChanged.emit()

    @Slot(Qt.CheckState)
    def on_maxi_enabled_changed(self, state: Qt.CheckState):
        """
        updates the model then send emits a "modelChanged" signal
        """
        # print("maximum enabled state changed")
        maxi_enabled = checkState2Bool(state)
        enabled = checkState2Bool(self.enabled_checkbox.checkState())
        self.maxi_spinbox.setEnabled(enabled and maxi_enabled)
        if maxi_enabled:
            self.model.maxi = self.maxi_spinbox.value()
        else:
            self.model.maxi = None
        self.modelChanged.emit()

    @Slot(SimpleParam)
    def load(self, model: SimpleParam):
        # print("Simple Param: loading model")
        check_state = bool2CheckState(model.enabled)
        self.on_enabled_changed(check_state)
        self.enabled_checkbox.setCheckState(check_state)
        self.mini_spinbox.setValue(model.mini)
        if model.maxi is not None:
            self.maxi_spinbox.setValue(model.maxi or model.mini)
        else:
            state = Qt.CheckState.Unchecked
            self.maxi_enabled_checkbox.setCheckState(state)
            self.on_maxi_enabled_changed(state)

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # print("Click SimpleParam")
            parent = self.parent()
            if isinstance(parent, SettingsFields):
                parent.clicked.emit(self.hint_id)
        else:
            super().mousePressEvent(event)


class MinDistField(QGroupBox):
    valueChanged: Signal = Signal(float)

    def __init__(
        self,
        value: float | None,
        parent: QWidget | None = None,
    ):
        super().__init__("Minimum distance", parent)
        self.setObjectName("Minimum_distance_field")

        layout = QHBoxLayout(self)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox(self)
        if value is not None:
            self.spinbox.setValue(value)
        self.spinbox.setMinimum(0.001)
        self.spinbox.setMaximum(4000)
        self.spinbox.setSingleStep(1)
        self.spinbox.setSuffix("px")
        layout.addWidget(self.spinbox)
        self.setLayout(layout)

        _ = self.spinbox.valueChanged.connect(self.valueChanged)

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # print("Click Min dist")
            parent = self.parent()
            if isinstance(parent, SettingsFields):
                parent.clicked.emit(Hint.MIN_DIST)
        else:
            super().mousePressEvent(event)


class NameField(QGroupBox):
    valueChanged: Signal = Signal(str)

    def __init__(self, color_name: str, parent: QWidget | None = None):
        super().__init__("Color name", parent)
        self.setObjectName("Name_field")
        layout = QHBoxLayout(self)
        self.field: QLineEdit = QLineEdit(color_name, self)
        layout.addWidget(self.field)
        self.setLayout(layout)

        _ = self.field.textChanged.connect(self.valueChanged)

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # print("Click name field")
            parent = self.parent()
            if isinstance(parent, SettingsFields):
                parent.clicked.emit(Hint.COLORS)
        else:
            super().mousePressEvent(event)


def checkState2Bool(check_state: Qt.CheckState) -> bool:
    if check_state == Qt.CheckState.Checked:
        return True
    else:
        return False


def bool2CheckState(value: bool) -> Qt.CheckState:
    if value:
        return Qt.CheckState.Checked
    else:
        return Qt.CheckState.Unchecked
