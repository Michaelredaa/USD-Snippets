import functools
import traceback
import math

from collections.abc import Iterable

from PySide2 import QtCore, QtGui, QtWidgets
from pxr import Sdf, Gf, Usd

WidgetRoleData = QtCore.Qt.UserRole + 10
valueRoleData = QtCore.Qt.UserRole + 20

KeyFrameColor = "#468C46"
timeSamplesColor = "#40806D"

## https://openusd.org/dev/api/_usd__page__datatypes.html
VALUE_TYPE_MAPPING = {
    # Scalar Types
    Sdf.ValueTypeNames.Bool: (bool, lambda: ValueWidget(1, type="bool")),
    Sdf.ValueTypeNames.UChar: (int, lambda: ValueWidget(1, type="int")),
    Sdf.ValueTypeNames.Int: (int, lambda: ValueWidget(1, type="int")),
    Sdf.ValueTypeNames.UInt: (int, lambda: ValueWidget(1, type="int")),
    Sdf.ValueTypeNames.Int64: (int, lambda: ValueWidget(1, type="int")),
    Sdf.ValueTypeNames.UInt64: (int, lambda: ValueWidget(1, type="int")),
    Sdf.ValueTypeNames.Half: (float, lambda: ValueWidget(1, type="float")),
    Sdf.ValueTypeNames.Float: (float, lambda: ValueWidget(1, type="float")),
    Sdf.ValueTypeNames.Double: (float, lambda: ValueWidget(1, type="float")),
    Sdf.ValueTypeNames.String: (str, lambda: ValueWidget(1, type="string")),
    Sdf.ValueTypeNames.Token: (str, lambda: TokensWidget(1)),
    Sdf.ValueTypeNames.Asset: (str, lambda: AssetWidget(1)),
    Sdf.ValueTypeNames.TimeCode: (float, lambda: ValueWidget(1, type="float")),
    #
    # # Vector Types
    Sdf.ValueTypeNames.Float2: (Gf.Vec2f, lambda: ValueWidget(2, type="float")),
    Sdf.ValueTypeNames.Float3: (Gf.Vec3f, lambda: ValueWidget(3, type="float")),
    Sdf.ValueTypeNames.Float4: (Gf.Vec4f, lambda: ValueWidget(4, type="float")),
    Sdf.ValueTypeNames.Double2: (Gf.Vec2d, lambda: ValueWidget(2, type="float")),
    Sdf.ValueTypeNames.Double3: (Gf.Vec3d, lambda: ValueWidget(3, type="float")),
    Sdf.ValueTypeNames.Double4: (Gf.Vec4d, lambda: ValueWidget(4, type="float")),
    Sdf.ValueTypeNames.Int2: (Gf.Vec2i, lambda: ValueWidget(2, type="int")),
    Sdf.ValueTypeNames.Int3: (Gf.Vec3i, lambda: ValueWidget(3, type="int")),
    Sdf.ValueTypeNames.Int4: (Gf.Vec4i, lambda: ValueWidget(4, type="int")),
    #
    # # Matrix Types
    Sdf.ValueTypeNames.Matrix2d: (Gf.Matrix2d, lambda: ValueMatrix(2)),
    Sdf.ValueTypeNames.Matrix3d: (Gf.Matrix3d, lambda: ValueMatrix(3)),
    Sdf.ValueTypeNames.Matrix4d: (Gf.Matrix4d, lambda: ValueMatrix(4)),
    #
    # Color Types
    Sdf.ValueTypeNames.Color3f: (Gf.Vec3f, lambda: ColorWidget(1, alpha=False)),
    Sdf.ValueTypeNames.Color4f: (Gf.Vec4f, lambda: ColorWidget(1, alpha=True)),

    # Quaternion Types
    Sdf.ValueTypeNames.Quatf: (Gf.Quatf, None),
    Sdf.ValueTypeNames.Quatd: (Gf.Quatd, None),
    Sdf.ValueTypeNames.Quath: (Gf.Quath, None),

    # Array Types (examples)
    Sdf.ValueTypeNames.BoolArray: (list, None),
    Sdf.ValueTypeNames.IntArray: (list, None),
    Sdf.ValueTypeNames.Float3Array: (list, None),
    Sdf.ValueTypeNames.DoubleArray: (list, None),
    Sdf.ValueTypeNames.Color3fArray: (list, None),
}


def is_scalar(variable):
    return isinstance(variable, (int, float, bool, complex, str, bytes, Sdf.AssetPath, Sdf.Path, type(None)))


def is_iterable(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (str, int, float))


def decompose_matrix(matrix):
    transform = Gf.Transform(matrix)
    translation = transform.GetTranslation()
    rotation = transform.GetRotation().Decompose(Gf.Vec3d(1, 0, 0), Gf.Vec3d(0, 1, 0),
                                                 Gf.Vec3d(0, 0, 1))  # Decomposes into Euler XYZ
    scale = transform.GetScale()
    return translation, rotation, scale


def compose_matrix(translation, rotation, scale):
    matrix = Gf.Matrix4d(1.0)

    rot = Gf.Rotation()
    roty = Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation[1])
    rotx = Gf.Rotation(Gf.Vec3d(1, 0, 0), rotation[0])
    rotz = Gf.Rotation(Gf.Vec3d(0, 0, 1), rotation[2])
    rot = rotx * roty * rotz

    rotation_matrix = Gf.Matrix3d(rot)
    for i in range(3):
        rotation_matrix.SetRow(i, rotation_matrix.GetRow(i) * scale[i])

    matrix.SetRotateOnly(rotation_matrix)

    matrix.SetTranslateOnly(Gf.Vec3d(*translation))

    return matrix


class ListItemSignalWrapper(QtCore.QObject):
    userRoleChanged = QtCore.Signal(QtWidgets.QListWidgetItem, object)


class ListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, widget):
        super().__init__()
        self.signal_wrapper = ListItemSignalWrapper()

    def setData(self, role, value):
        if role == valueRoleData:
            current_value = self.data(role)
            if current_value != value:
                super().setData(role, value)
                self.signal_wrapper.userRoleChanged.emit(self, value)
        else:
            super().setData(role, value)


class CustomEventFilter(QtCore.QObject):
    actionSignal = QtCore.Signal(str)
    resetSignal = QtCore.Signal()

    def __init__(self, widget):
        super().__init__()

        self.widget = widget
        self.widget.contextMenuEvent = self.contextMenuEvent
        if isinstance(widget, (QtWidgets.QComboBox, QtWidgets.QAbstractSpinBox)):
            self.widget.lineEdit().installEventFilter(self)
        else:
            self.widget.installEventFilter(self)

    def contextMenuEvent(self, event):
        print("Context")
        context_menu = QtWidgets.QMenu()
        reset_action = QtWidgets.QAction('Reset')
        reset_action.triggered.connect(self.resetSignal.emit)

        context_menu.addAction(reset_action)

        context_menu.exec_(event.globalPos())

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:

                if event.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ShiftModifier):
                    self.change_background_color(reset=True)
                    self.actionSignal.emit("lt+alt+shift")

                if event.modifiers() == QtCore.Qt.AltModifier:
                    self.change_background_color(color=KeyFrameColor)
                    self.actionSignal.emit("lt+alt")

        return super().eventFilter(obj, event)

    def change_background_color(self, color="", reset=False):
        if reset:
            self.widget.setStyleSheet("")
        else:
            self.widget.setStyleSheet("background-color: {};".format(color))


class CheckBox(QtWidgets.QCheckBox):
    changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_filter = CustomEventFilter(self)

        self.stateChanged.connect(self.changed.emit)

    @property
    def data(self):
        return self.value()

    @data.setter
    def data(self, value):
        self.setChecked(value)


class SpinBox(QtWidgets.QSpinBox):
    changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_filter = CustomEventFilter(self)

        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setRange(-2147483647, 2147483647)

        self.editingFinished.connect(lambda: self.changed.emit(self.value()))

    @property
    def data(self):
        return self.value()

    @data.setter
    def data(self, value):
        self.setValue(value)


class DoubleSpinBox(QtWidgets.QDoubleSpinBox):
    changed = QtCore.Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_filter = CustomEventFilter(self)

        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setDecimals(10)
        self.setRange(-2147483647.0, 2147483647.0)

        self.editingFinished.connect(lambda: self.changed.emit(self.value()))

    def textFromValue(self, value):
        formatted_value = str(value).rstrip('0').rstrip('.')
        return formatted_value

    @property
    def data(self):
        return self.value()

    @data.setter
    def data(self, value):
        self.setValue(value)


class LineEdit(QtWidgets.QLineEdit):
    changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_filter = CustomEventFilter(self)

        self.editingFinished.connect(lambda: self.changed.emit(self.text()))

    @property
    def data(self):
        return self.text()

    @data.setter
    def data(self, value):
        self.setText(value)


class LineEditTokens(QtWidgets.QComboBox):
    changed = QtCore.Signal(str)

    def __init__(self, tokens=None, parent=None):
        super().__init__(parent)

        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.addItems(list(tokens))
        self.setCompleter(QtWidgets.QCompleter(self.model()))
        # self.lineEdit().editingFinished.connect(lambda: self.changed.emit(self.lineEdit().text()))
        self.currentTextChanged.connect(self.changed.emit)

        self.event_filter = CustomEventFilter(self)

    def set(self, value):
        self.setCurrentText(value)


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ColorFiled(QtWidgets.QWidget):
    changed = QtCore.Signal(str)
    actionSignal = QtCore.Signal(object)

    def __init__(self, alpha=False, parent=None):
        super().__init__(parent)

        self.alpha = alpha
        self.items = []

        layout = QtWidgets.QHBoxLayout()
        self.color_label = ClickableLabel()
        self.color_label.setFixedWidth(50)
        layout.addWidget(self.color_label)

        self.color_dialog = QtWidgets.QColorDialog()
        self.color_dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, self.alpha)

        for i in range(3 + int(self.alpha)):
            item = DoubleSpinBox()
            item.setRange(0.0, 1.0)
            item.setSingleStep(0.01)
            layout.addWidget(item)
            item.valueChanged.connect(self.changed.emit)
            item.valueChanged.connect(self.update_from_spinboxes)
            item.event_filter.actionSignal.connect(self.actionSignal.emit)
            self.items.append(item)

        self.setLayout(layout)

        # Signals
        self.color_label.clicked.connect(self.open_color_dialog)
        self.color_dialog.currentColorChanged.connect(self.update_from_color_picker)

    @property
    def rgba(self):
        return [item.value() for item in self.items]

    @rgba.setter
    def rgba(self, values):
        [self.items[i].setValue(v) for i, v in enumerate(values)]

    @property
    def data(self):
        return self.rgba

    @data.setter
    def data(self, value):
        if isinstance(value, list):
            value = value[0]
        self.rgba = value

    @property
    def color(self):
        return QtGui.QColor(*[c * 255 for c in self.rgba])

    def open_color_dialog(self):
        self.color_dialog.setCurrentColor(self.color)
        self.color_dialog.open()

    def update_from_color_picker(self, color):
        if color.isValid():
            rgba = color.getRgb()
            for i in range(3 + int(self.alpha)):
                self.items[i].setValue(rgba[i] / 255.0)
            self.update_label_color(color)

    def update_label_color(self, color):
        self.color_label.setStyleSheet(f"background-color: {color.name()};")

    def update_from_spinboxes(self):
        color_values = [int(item.value() * 255) for item in self.items]
        self.update_label_color(QtGui.QColor(*color_values))


class EditAttrWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewer = None
        self.prop = None
        self.setLayout(QtWidgets.QHBoxLayout())

        self.list_attr_widget = EditListAttrWidget()
        self.list_rel_widget = EditListRelationshipWidget()
        self.layout().addWidget(self.list_attr_widget)
        self.layout().addWidget(self.list_rel_widget)

    def populate(self, prop, viewer):
        self.viewer = viewer
        self.prop = prop

        if isinstance(prop, Usd.Attribute):
            self.list_attr_widget.setHidden(False)
            self.list_rel_widget.setHidden(True)
            self.property_is_attr(prop)
        else:
            self.list_attr_widget.setHidden(True)
            self.list_rel_widget.setHidden(False)
            self.property_is_relationship(prop)

    def property_is_attr(self, attr):

        self.attr = attr
        self.keyframes = {}
        self.time_sample_cb = QtWidgets.QCheckBox("Update with timeSample")
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.key_btn = QtWidgets.QPushButton("Key")

        btn_layout = QtWidgets.QHBoxLayout(self)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.key_btn)

        self.list_attr_widget.reset()
        type_name = attr.GetTypeName()
        python_type, widget_factory = VALUE_TYPE_MAPPING.get(type_name, (None, None))

        if widget_factory is None:
            print(f"Unsupported type: {type_name}")
            return

        self.list_attr_widget._update = True
        self.list_attr_widget._attr = attr
        self.list_attr_widget.viewer = self.viewer
        self.list_attr_widget.widget_factory = widget_factory
        self.list_attr_widget.python_type = python_type
        self.update_attribute_value(attr)
        self.list_attr_widget.add_item()

        self.list_attr_widget.valueChanged.connect(self.on_attr_value_changed)

        app_controller = self.viewer._UsdviewApi__appController
        app_controller._ui.frameSlider.sliderReleased.connect(
            functools.partial(self.update_attribute_value, attr))

    def property_is_relationship(self, prop):

        self.list_rel_widget.rel = prop
        self.list_rel_widget.populate()

    def update_attribute_value(self, attr):
        self.list_attr_widget.value = attr.Get(self.frame())

    def on_attr_value_changed(self, value_modifier, *args):
        value, modifier = value_modifier

        values = value
        if len(values) == 1:
            values = value[0]
        python_type = self.list_attr_widget.python_type

        if modifier == "lt+alt":
            self.keyframes[self.viewer.frame] = values
            for frame, t_values in self.keyframes.items():
                self.attr.Set(python_type(t_values), frame)

        elif modifier == "lt+alt+shift":
            self.keyframes = {}
            self.attr.Clear()
            self.attr.Set(python_type(values), self.frame())
            self.list_attr_widget._update = True

        else:
            self.attr.Set(python_type(values), self.frame())

    def frame(self):
        frame = self.viewer.frame if self.attr.GetNumTimeSamples() else Usd.TimeCode.Default()
        return frame


class EditListRelationshipWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._rel = None

        self._widget = None
        self._widget_factory = None

        self.layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        self.layout.addWidget(self.list_widget)

        self.setLayout(self.layout)

    @property
    def rel(self):
        return self._rel

    @rel.setter
    def rel(self, rel):
        self._rel = rel

    @property
    def targets(self):
        if self._rel:
            return self._rel.GetTargets()
        return []

    @targets.setter
    def targets(self, targets):
        if self._rel:
            self._rel.SetTargets(targets)

    def populate(self):
        for target in self.targets:
            widget = QtWidgets.QLineEdit()
            widget.setText(target.pathString)
            item = self.add_item(widget)
            widget.editingFinished.connect(lambda: self.update_item_data(widget, item))

    def add_item(self, widget):
        widget_item = QtWidgets.QListWidgetItem(self.list_widget)

        widget_item.setSizeHint(widget.sizeHint())
        widget_item.setFlags(QtCore.Qt.NoItemFlags)

        self.list_widget.addItem(widget_item)
        self.list_widget.setItemWidget(widget_item, widget)
        return widget_item

    def reset(self):
        self.list_widget.clear()

    def update_item_data(self, widget, item):
        item.setData(QtCore.Qt.UserRole, widget.text())

        targets = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            target = item.data(QtCore.Qt.UserRole)
            targets.append(target)

        self.targets = targets


class EditListAttrWidget(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._attr = None
        self._value = []
        self._update = False
        self._python_type = bool

        self.is_array = False

        self._widget_factory = None
        self._time_sample_update = False
        self._keyframes = {}

        self.layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        self.layout.addWidget(self.list_widget)
        self.setLayout(self.layout)

    @property
    def widget_factory(self):
        return self._widget_factory

    @widget_factory.setter
    def widget_factory(self, _widget_factory):
        self._widget_factory = _widget_factory

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if is_scalar(value):
            value = [value]
        self._value = value

        item = self.list_widget.item(0)
        if item and self.is_time_sample(widget=item.data(WidgetRoleData)):
            self.set_item_data(value_modifier=[value, None], item=item)

    def populate(self):
        self.add_item()

    def add_item(self):
        widget = self._widget_factory()
        widget._attr = self._attr
        widget.parent_widget = self
        widget.construct()
        widget.values = self._value

        if self.is_time_sample(widget=widget):
            widget._update = self._update = False
        else:
            widget._update = self._update = True

        widget_item = ListWidgetItem(self.list_widget)
        widget_item.setSizeHint(widget.sizeHint())
        widget_item.setFlags(QtCore.Qt.NoItemFlags)
        widget_item.setData(valueRoleData, [self._value, None])

        self.list_widget.addItem(widget_item)
        self.list_widget.setItemWidget(widget_item, widget)

        widget_item.setData(WidgetRoleData, widget)

        widget.valueChanged.connect(
            lambda value_modifier: self.set_item_data(value_modifier=value_modifier, item=widget_item))
        widget_item.signal_wrapper.userRoleChanged.connect(self.on_value_changed)

    def set_item_data(self, value_modifier, item, *args):

        widget = item.data(WidgetRoleData)
        if widget:
            self.is_time_sample(widget=widget)
            item.setData(valueRoleData, value_modifier)

    def on_value_changed(self, item, value_modifier):
        value, modifier = value_modifier
        widget = item.data(WidgetRoleData)
        widget.values = value

        if self._update and not self.is_time_sample(widget=widget):
            self.valueChanged.emit(value_modifier)

        elif modifier:
            widget._update = self._update = False
            self.valueChanged.emit(value_modifier)

    def delete_all_items(self):
        self.list_widget.clear()

    def remove_item_by_index(self, idx=0):
        if 0 <= idx < self.list_widget.count():
            item = self.list_widget.takeItem(idx)
            del item

    def reset(self):
        self.delete_all_items()

    def is_time_sample(self, widget=None):
        if self._attr and self._attr.GetNumTimeSamples() > 1:
            if widget:
                widget.setStyleSheet("background-color: {};".format(timeSamplesColor))
            return True
        else:
            widget.setStyleSheet("")
            return False


class ValueBase(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(object)
    """
    - values = values
    - construct()
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.size = 0
        self._attr = None
        self.parent_widget = None
        self._update = False  # Emit signals
        self._values = []
        self.attr_widgets = []

        self.values_layout = QtWidgets.QVBoxLayout()

        self.setLayout(self.values_layout)

    def on_value_changed(self, modifier=None, *args):
        if self._update or modifier:
            values = self.get_widget_values()
            self.valueChanged.emit([values, modifier])

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        self.update_widget_values()

    def construct(self):
        self._construct()

    def _construct(self):
        pass

    def update_widget_values(self):
        pass

    def get_widget_values(self):
        return []

    def on_keyframe(self, modifier):
        # self._update = False
        self.on_value_changed(modifier=modifier)

    def on_rest_attr(self):
        if self._attr:
            self._attr.Clear()
            # self._values = self._attr.Get()
            self.update_widget_values()


Widget_Types = {
    "int": SpinBox,
    "float": DoubleSpinBox,
    "bool": CheckBox,
    "string": LineEdit
}


class ValueWidget(ValueBase):

    def __init__(self, size=1, type="int", parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.type = type

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            widget_f = Widget_Types.get(self.type)
            if not widget_f:
                print("Unsupported Widget")
                return
            widget = widget_f()
            layout.addWidget(widget)
            widget.changed.connect(lambda: self.on_value_changed(modifier=None))
            widget.event_filter.actionSignal.connect(self.on_keyframe)
            widget.event_filter.resetSignal.connect(self.on_rest_attr)

            self.attr_widgets.append(widget)

        self.values_layout.addLayout(layout)

    def update_widget_values(self):
        if not self._values:
            print("No values")
            return

        print("setting values w:: ", self._values)
        for i in range(self.size):
            self.attr_widgets[i].data = self._values[i]

    def get_widget_values(self):
        self._values = [self.attr_widgets[i].data for i in range(self.size)]
        return self._values


class TokensWidget(ValueWidget):

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        if not self._attr:
            return

        tokens = self._attr.GetMetadata("allowedTokens") or []
        for i in range(self.size):
            widget = LineEditTokens(tokens=tokens)
            layout.addWidget(widget)
            widget.changed.connect(self.on_value_changed)

            widget.event_filter.actionSignal.connect(self.on_keyframe)
            self.attr_widgets.append(widget)

        self.values_layout.addLayout(layout)


class AssetWidget(ValueBase):

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            resolve_cb = QtWidgets.QCheckBox("", self)
            resolve_cb.setToolTip("Resolve Path")
            layout.addWidget(resolve_cb)
            widget = LineEdit()
            layout.addWidget(widget)

            resolve_cb.stateChanged.connect(functools.partial(self.on_resolve, widget))
            widget.event_filter.actionSignal.connect(self.on_keyframe)

            self.attr_widgets.append(widget)

        self.values_layout.addLayout(layout)

    def update_widget_values(self):
        if not self._values:
            print("No values")
            return

        for i in range(self.size):
            self.attr_widgets[i].data = self._values[i].path

    def get_widget_values(self):
        self._values = [self.attr_widgets[i].data for i in range(self.size)]
        return self._values

    def on_resolve(self, widget, checked):
        text = self._values[0]
        if checked and self._attr:
            stage = self._attr.GetStage()
            resolved_text = stage.ResolveIdentifierToEditTarget(widget.text())
            widget.setText(resolved_text)
        else:
            widget.setText(text.path)


class ColorWidget(ValueBase):
    def __init__(self, size=1, alpha=False, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.alpha = alpha

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            widget = ColorFiled(alpha=self.alpha)
            layout.addWidget(widget)
            widget.changed.connect(self.on_value_changed)
            widget.actionSignal.connect(self.on_keyframe)
            self.attr_widgets.append(widget)

        self.values_layout.addLayout(layout)

    def update_widget_values(self):
        if not self._values:
            print("No values")
            return

        for i in range(self.size):
            self.attr_widgets[i].data = self._values

    def get_widget_values(self):
        self._values = [self.attr_widgets[i].data for i in range(self.size)]
        return self._values


class ValueMatrix(ValueBase):

    def __init__(self, size, parent=None):
        super().__init__(parent=parent)
        self.size = size

        self._trs_matrix = self.size == 4
        self.trs_items = []

        self.matrix_widget = QtWidgets.QWidget()
        self.trs_widget = QtWidgets.QWidget()

    def _construct(self):
        layout = QtWidgets.QVBoxLayout()
        if self._trs_matrix:
            trs_cb = QtWidgets.QCheckBox("TRS")
            trs_cb.setChecked(True)
            trs_cb.stateChanged.connect(self.on_trs_cb_changes)
            layout.addWidget(trs_cb)

        matrix_layout = QtWidgets.QVBoxLayout()
        for r in range(self.size):
            r_layout = QtWidgets.QHBoxLayout()
            row_items = []
            for c in range(self.size):
                item = DoubleSpinBox()

                item.changed.connect(lambda: self.on_value_changed(modifier=None))
                item.event_filter.actionSignal.connect(self.on_keyframe)

                row_items.append(item)
                r_layout.addWidget(item)

            matrix_layout.addLayout(r_layout)
            self.attr_widgets.append(row_items)

        trs_layout = QtWidgets.QVBoxLayout()
        if self._trs_matrix:
            labels = ["Translate", "Rotate", "Scale"]
            for c in range(self.size - 1):
                t_layout = QtWidgets.QHBoxLayout()
                row_items = []
                for r in range(self.size):
                    if r == 0:
                        label = QtWidgets.QLabel(labels[c])
                        t_layout.addWidget(label)
                        continue

                    item = DoubleSpinBox()

                    item.changed.connect(lambda: self.on_trs_value_changed())
                    item.event_filter.actionSignal.connect(self.on_keyframe)

                    row_items.append(item)
                    t_layout.addWidget(item)

                trs_layout.addLayout(t_layout)
                self.trs_items.append(row_items)

            self.matrix_widget.setHidden(True)
            self.trs_widget.setLayout(trs_layout)
            layout.addWidget(self.trs_widget)

        self.matrix_widget.setLayout(matrix_layout)
        layout.addWidget(self.matrix_widget)

        self.values_layout.addLayout(layout)

    def on_trs_cb_changes(self, status):
        self.matrix_widget.setHidden(bool(status))
        self.trs_widget.setHidden(not bool(status))

    def on_trs_value_changed(self):
        values = []
        for r in range(len(self.trs_items)):
            row_values = []
            for c in range(len(self.trs_items[r])):
                row_values.append(self.trs_items[r][c].value())
            values.append(row_values)
        self._values = compose_matrix(*values)  # matrix
        self.update_widget_values(update_trs=False)
        self.on_value_changed(modifier=None)

    def update_widget_values(self, update_trs=True):
        if not self._values:
            print("No values")
            return
        for r in range(self.size):
            for c in range(self.size):
                self.attr_widgets[r][c].data = self._values[r][c]

        if update_trs:
            self.update_trs_value()

    def get_widget_values(self):
        values = []
        for r in range(self.size):
            row_values = []
            for c in range(self.size):
                row_values.append(self.attr_widgets[r][c].data)
            values.append(row_values)

        self._values = Gf.Matrix4d(values)
        return self._values

    def trs_values(self):
        values = []
        for r in range(len(self.trs_items)):
            for c in range(len(self.trs_items[r])):
                values.append(self.trs_items[r][c].value())
        return values

    def update_trs_value(self, *args):
        trs_values = decompose_matrix(self._values)
        for r in range(len(self.trs_items)):
            for c in range(len(trs_values[r])):
                self.trs_items[r][c].setValue(trs_values[r][c])
