from typing_extensions import override
from random import randint

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QSpinBox,
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

from spot_detector.model.models import DetParams, SimpleParam, Threshold
from spot_detector.types import Hint


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
            self.model = DetParams.from_defaults(f"unnamed_color_{randint(0, 65535)}")
        else:
            self.model = model.model_copy(deep=True)

        layout = QVBoxLayout(self)
        layout.setObjectName("Settings_Fields_layout")
        self.name_field = NameField(self.model.color_name, self)  # TODO: Handle Hint
        layout.addWidget(self.name_field)
        self.min_dist = MinDistField(self.model.min_dist, self)  # TODO: Handle Hint
        layout.addWidget(self.min_dist)
        self.thresh = TresholdWidget(self.model.thresh, self)
        layout.addWidget(self.thresh)
        self.area = SimpleParamWidget(
            "Filter by Area", Hint.AREA, self.model.area, 4000, 1, self
        )
        layout.addWidget(self.area)

        self.convex = SimpleParamWidget(
            "Filter by Convexity", Hint.CONV, self.model.convex, 1, 0.05, self
        )
        layout.addWidget(self.convex)

        self.circ = SimpleParamWidget(
            "Filter by Circularity", Hint.CIRC, self.model.circ, 1, 0.05, self
        )
        layout.addWidget(self.circ)

        self.inertia = SimpleParamWidget(
            "Filter by Inertia", Hint.INERTIA, self.model.inertia, 1, 0.05, self
        )
        layout.addWidget(self.inertia)

        layout.addStretch(1)
        self.setLayout(layout)

        self.name_field.valueChanged.connect(self.change_color_name)
        self.min_dist.valueChanged.connect(self.change_min_dist)
        self.thresh.modelChanged.connect(self.emit_new_model)
        self.area.modelChanged.connect(self.emit_new_model)
        self.convex.modelChanged.connect(self.emit_new_model)
        self.circ.modelChanged.connect(self.emit_new_model)
        self.inertia.modelChanged.connect(self.emit_new_model)

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
        self.name_field.field.setText(model.color_name)
        self.min_dist.spinbox.setValue(model.min_dist or 0)
        self.thresh.load(model.thresh)
        self.area.load(model.area)
        self.convex.load(model.convex)
        self.circ.load(model.circ)
        self.inertia.load(model.inertia)

    @Slot()
    def emit_new_model(self):
        """
        Upon update, children widgets emit a signal that get caught by this
        function. Then a different signal is emited containing a copy of the
        new model.
        """
        self.modelChanged.emit(self.model.model_copy(deep=True))


class TresholdWidget(QGroupBox):
    modelChanged = Signal()

    def __init__(
        self,
        model: Threshold,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Detection Thresholds", parent)
        self.setObjectName("Threshold_param_widget")

        self.model = model

        layout = QVBoxLayout(self)
        layout.setObjectName("Threshold_layout")
        self.automatic_checkbox = QCheckBox("Automatic", self)
        check_state = bool2CheckState(not self.model.automatic)
        self.automatic_checkbox.setCheckState(check_state)
        layout.addWidget(self.automatic_checkbox)

        mini_layout = QHBoxLayout()
        mini_layout.setObjectName("Threshold_layout_mini")
        mini_layout.addWidget(QLabel("Minimum", self))
        self.mini_spinbox = QSpinBox(self)
        self.mini_spinbox.setMinimum(0)
        self.mini_spinbox.setMaximum(255)
        self.mini_spinbox.setValue(self.model.mini)
        mini_layout.addWidget(self.mini_spinbox)
        layout.addLayout(mini_layout)

        maxi_layout = QHBoxLayout()
        maxi_layout.setObjectName("Threshold_layout_maxi")
        maxi_layout.addWidget(QLabel("Maximum", self))
        self.maxi_spinbox = QSpinBox(self)
        self.maxi_spinbox.setMinimum(0)
        self.maxi_spinbox.setMaximum(255)
        self.maxi_spinbox.setValue(self.model.maxi)
        maxi_layout.addWidget(self.maxi_spinbox)
        layout.addLayout(maxi_layout)

        step_layout = QHBoxLayout()
        step_layout.setObjectName("Threshold_layout_step")
        step_layout.addWidget(QLabel("Step", self))
        self.step_spinbox = QSpinBox(self)
        self.step_spinbox.setMinimum(0)
        self.step_spinbox.setMaximum(255)
        self.step_spinbox.setValue(self.model.step)
        step_layout.addWidget(self.step_spinbox)
        layout.addLayout(step_layout)

        self.mini_spinbox.valueChanged.connect(self.on_mini_changed)
        self.maxi_spinbox.valueChanged.connect(self.on_maxi_changed)
        self.automatic_checkbox.checkStateChanged.connect(self.on_automatic_changed)
        self.on_automatic_changed(self.automatic_checkbox.checkState())

    @Slot(Qt.CheckState)
    def on_automatic_changed(self, state: Qt.CheckState):
        value = False if state == Qt.CheckState.Checked else True
        self.mini_spinbox.setEnabled(value)
        self.maxi_spinbox.setEnabled(value)
        self.step_spinbox.setEnabled(value)
        self.model.automatic = value
        self.modelChanged.emit()  # TODO: fix type signature

    def load(self, model: Threshold):
        check_state = bool2CheckState(model.automatic)
        self.on_automatic_changed(check_state)
        self.automatic_checkbox.setCheckState(check_state)
        self.mini_spinbox.setValue(model.mini)
        self.maxi_spinbox.setValue(model.maxi)
        self.step_spinbox.setValue(model.step)

    @Slot(int)
    def on_mini_changed(self, value: int):
        """
        updates the model then send emits a "modelChanged" signal
        """
        self.maxi_spinbox.setMinimum(value)
        self.model.mini = value
        self.modelChanged.emit()  # TODO: fix type signature

    @Slot(int)
    def on_maxi_changed(self, value: int):
        """
        updates the model then send emits a "modelChanged" signal
        """
        self.mini_spinbox.setMaximum(value)
        self.model.maxi = value
        self.modelChanged.emit()  # TODO: fix type signature

    def get_model(self):
        return self.model

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # print("Click Threshold")
            parent = self.parent()
            if isinstance(parent, SettingsFields):
                parent.clicked.emit(Hint.THRESH)
        else:
            super().mousePressEvent(event)


class SimpleParamWidget(QGroupBox):
    modelChanged = Signal()

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

        self.model = model

        self.hint_id = hint_id

        # Main Parameter Enabled checkbox
        layout = QVBoxLayout(self)
        layout.setObjectName("Simple_Param_layout")
        self.enabled_checkbox = QCheckBox("Enabled", self)
        check_state = bool2CheckState(self.model.enabled)
        self.enabled_checkbox.setCheckState(check_state)
        layout.addWidget(self.enabled_checkbox)

        mini_layout = QHBoxLayout()
        mini_layout.addWidget(QLabel("Minimum", self))
        self.mini_spinbox = QDoubleSpinBox(self)
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
        self.maxi_enabled_checkbox = QCheckBox("Maximum", self)
        check_state = bool2CheckState(self.model.maxi is not None)
        self.maxi_enabled_checkbox.setCheckState(check_state)
        maxi_layout.addWidget(self.maxi_enabled_checkbox)
        self.maxi_spinbox = QDoubleSpinBox(self)
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
        self.mini_spinbox.valueChanged.connect(self.on_mini_changed)
        self.maxi_spinbox.valueChanged.connect(self.on_maxi_changed)
        self.enabled_checkbox.checkStateChanged.connect(self.on_enabled_changed)
        self.maxi_enabled_checkbox.checkStateChanged.connect(
            self.on_maxi_enabled_changed
        )

    @Slot(float)
    def on_maxi_changed(self, value):
        """
        updates the model then send emits a "modelChanged" signal
        """
        self.mini_spinbox.setMaximum(value)
        self.model.maxi = value
        self.modelChanged.emit()

    @Slot(float)
    def on_mini_changed(self, value):
        """
        updates the model then send emits a "modelChanged" signal
        """
        self.maxi_spinbox.setMinimum(value)
        self.model.mini = value
        self.modelChanged.emit()

    @Slot(Qt.CheckState)
    def on_enabled_changed(self, state: Qt.CheckState):
        """
        updates the model then send emits a "modelChanged" signal
        """
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
        self.spinbox = QDoubleSpinBox(self)
        if value is not None:
            self.spinbox.setValue(value)
        self.spinbox.setMinimum(0.001)
        self.spinbox.setMaximum(4000)
        self.spinbox.setSingleStep(1)
        self.spinbox.setSuffix("px")
        layout.addWidget(self.spinbox)
        self.setLayout(layout)

        self.spinbox.valueChanged.connect(self.valueChanged)

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
        self.field = QLineEdit(color_name, self)
        layout.addWidget(self.field)
        self.setLayout(layout)

        self.field.textChanged.connect(self.valueChanged)

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
