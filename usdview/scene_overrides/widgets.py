import functools
import traceback
import math

from collections.abc import Iterable

from PySide2 import QtCore, QtGui, QtWidgets
from pxr import Sdf, Gf, Usd

## https://openusd.org/dev/api/_usd__page__datatypes.html
VALUE_TYPE_MAPPING = {
    # Scalar Types
    Sdf.ValueTypeNames.Bool: (bool, lambda: ValueBool(1)),
    Sdf.ValueTypeNames.UChar: (int, lambda: ValueInt(1)),
    Sdf.ValueTypeNames.Int: (int, lambda: ValueInt(1)),
    Sdf.ValueTypeNames.UInt: (int, lambda: ValueInt(1)),
    Sdf.ValueTypeNames.Int64: (int, lambda: ValueInt(1)),
    Sdf.ValueTypeNames.UInt64: (int, lambda: ValueInt(1)),
    Sdf.ValueTypeNames.Half: (float, lambda: ValueDouble(1)),
    Sdf.ValueTypeNames.Float: (float, lambda: ValueDouble(1)),
    Sdf.ValueTypeNames.Double: (float, lambda: ValueDouble(1)),
    Sdf.ValueTypeNames.String: (str, lambda: ValueString(1)),
    Sdf.ValueTypeNames.Token: (str, lambda: ValueToken(1)),
    Sdf.ValueTypeNames.Asset: (str, lambda: ValueAsset(1)),
    Sdf.ValueTypeNames.TimeCode: (float, lambda: ValueDouble(1)),

    # Vector Types
    Sdf.ValueTypeNames.Float2: (Gf.Vec2f, lambda: ValueDouble(2)),
    Sdf.ValueTypeNames.Float3: (Gf.Vec3f, lambda: ValueDouble(3)),
    Sdf.ValueTypeNames.Float4: (Gf.Vec4f, lambda: ValueDouble(4)),
    Sdf.ValueTypeNames.Double2: (Gf.Vec2d, lambda: ValueDouble(2)),
    Sdf.ValueTypeNames.Double3: (Gf.Vec3d, lambda: ValueDouble(3)),
    Sdf.ValueTypeNames.Double4: (Gf.Vec4d, lambda: ValueDouble(4)),
    Sdf.ValueTypeNames.Int2: (Gf.Vec2i, lambda: ValueInt(2)),
    Sdf.ValueTypeNames.Int3: (Gf.Vec3i, lambda: ValueInt(3)),
    Sdf.ValueTypeNames.Int4: (Gf.Vec4i, lambda: ValueInt(4)),

    # Matrix Types
    Sdf.ValueTypeNames.Matrix2d: (Gf.Matrix2d, lambda: ValueMatrix(2)),
    Sdf.ValueTypeNames.Matrix3d: (Gf.Matrix3d, lambda: ValueMatrix(3)),
    Sdf.ValueTypeNames.Matrix4d: (Gf.Matrix4d, lambda: ValueMatrix(4)),

    # Color Types
    Sdf.ValueTypeNames.Color3f: (Gf.Vec3f, lambda: ValueColor(1, alpha=False)),
    Sdf.ValueTypeNames.Color4f: (Gf.Vec4f, lambda: ValueColor(1, alpha=True)),

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


def get_widget_from_python_type(_type):
    for _type_name, values in VALUE_TYPE_MAPPING.items():
        if _type == values[0]:
            return _type_name


def is_iterable(variable):
    return isinstance(variable, Iterable) and not isinstance(variable, (str, bytes))


def is_scalar(variable):
    return isinstance(variable, (int, float, bool, complex, str, bytes, type(None)))


def clear_layout(layout):
    """
    Safely clear the layout and delete all its widgets.
    """
    if not layout:
        return

    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        else:
            layout.removeItem(item)

        QtCore.QCoreApplication.sendPostedEvents()


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


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ColorWidget(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(object)

    def __init__(self, alpha=False, parent=None):

        super().__init__(parent=parent)

        self.alpha = alpha
        self.items = []

        layout = QtWidgets.QHBoxLayout()
        self.color_label = ClickableLabel()
        self.color_label.setFixedWidth(50)
        layout.addWidget(self.color_label)

        self.color_dialog = QtWidgets.QColorDialog()
        self.color_dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, self.alpha)

        for i in range(3 + int(self.alpha)):
            item = QtWidgets.QDoubleSpinBox()
            item.setRange(0.0, 1.0)
            item.setSingleStep(0.01)
            layout.addWidget(item)
            item.valueChanged.connect(self.valueChanged.emit)
            item.valueChanged.connect(self.update_from_spinboxes)
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
        layout = QtWidgets.QHBoxLayout()

        self.list_attr_widget = EditListAttrWidget()
        self.list_rel_widget = EditListRelationshipWidget()
        layout.addWidget(self.list_attr_widget)
        layout.addWidget(self.list_rel_widget)

        self.setLayout(layout)

    def populate(self, prop, viewer):
        self.viewer = viewer

        if isinstance(prop, Usd.Attribute):
            self.list_attr_widget.setHidden(False)
            self.list_rel_widget.setHidden(True)
            self.property_is_attr(prop)
        else:
            self.list_attr_widget.setHidden(True)
            self.list_rel_widget.setHidden(False)
            self.property_is_relationship(prop)

    def property_is_attr(self, attr):
        self.list_attr_widget.reset()
        type_name = attr.GetTypeName()
        if attr.GetTypeName().isArray:
            if attr.HasValue():
                elem_python_type = type(attr.Get()[0])
                type_name = get_widget_from_python_type(elem_python_type)

        python_type, widget_factory = VALUE_TYPE_MAPPING.get(type_name, (None, None))

        if widget_factory is None:
            print(f"Unsupported type: {attr.GetTypeName()}")
            return

        widget_instance = widget_factory()
        self.list_attr_widget.attr = attr
        self.list_attr_widget.frame = self.viewer.frame
        self.list_attr_widget.widget_factory = widget_factory
        self.list_attr_widget.widget = widget_instance
        self.list_attr_widget.python_type = python_type
        widget_instance.construct()
        self.list_attr_widget.populate()

        app_controller = self.viewer._UsdviewApi__appController
        app_controller._ui.frameSlider.sliderReleased.connect(
            functools.partial(self.set_attribute_value, widget_instance))

    def property_is_relationship(self, prop):
        self.list_rel_widget.rel = prop
        self.list_rel_widget.populate()

    def set_attribute_value(self, widget_instance):
        widget_instance.frame = self.viewer.frame
        widget_instance.update()


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
        return self._attr

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
    def __init__(self, parent=None):
        super().__init__(parent)

        self.size = 0
        self._attr = None
        self._update = False
        self._frame = Usd.TimeCode.Default()
        self._python_type = bool

        self.is_array = False
        self.array_elem_type = bool

        self._widget = None
        self._widget_factory = None
        self._time_sample_update = False

        self.layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()

        self.time_sample_cb = QtWidgets.QCheckBox("Update with timeSample")
        self.layout.addWidget(self.time_sample_cb)
        self.layout.addWidget(self.list_widget)

        self.time_sample_cb.stateChanged.connect(self.on_time_sample_changes)

        self.setLayout(self.layout)

    @property
    def attr(self):
        return self._attr

    @attr.setter
    def attr(self, attr):
        self._attr = attr
        self.is_array = attr.GetTypeName().isArray

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if self.attr is None:
            return
        if self.is_time_sample():
            self._frame = Usd.TimeCode(value)
        else:
            self._frame = Usd.TimeCode.Default()

    @property
    def attr_value(self):
        return self._attr.Get(self._frame)

    @attr_value.setter
    def attr_value(self, value):
        if self.attr is None:
            return
        self.attr.Set(value, self.frame)

    @property
    def widget(self):
        return self._widget

    @widget.setter
    def widget(self, widget):
        self._widget = widget

        self._widget.attr = self._attr
        self._widget.frame = self._frame
        self._widget.valueChanged.connect(self.set_attr)

    @property
    def widget_factory(self):
        return self._widget_factory

    @widget_factory.setter
    def widget_factory(self, _widget_factory):
        self._widget_factory = _widget_factory

    @property
    def python_type(self):
        return self._python_type

    @python_type.setter
    def python_type(self, python_type):
        self._python_type = python_type

    def populate(self):
        self.add_item(self._widget)

        if self._time_sample_update:
            self._update = False
        else:
            self._update = True

    def is_time_sample(self):
        return bool(self.attr.GetNumTimeSamples())

    def add_item(self, widget):
        widget_item = QtWidgets.QListWidgetItem(self.list_widget)

        widget_item.setSizeHint(widget.sizeHint())
        widget_item.setFlags(QtCore.Qt.NoItemFlags)

        self.list_widget.addItem(widget_item)
        self.list_widget.setItemWidget(widget_item, widget)

        widget.valueChanged.connect(self.set_attr)

    def delete_all_items(self):
        self.list_widget.clear()

    def remove_item_by_index(self, idx=0):
        if 0 <= idx < self.list_widget.count():
            item = self.list_widget.takeItem(idx)
            del item

    def reset(self):
        self.delete_all_items()

    def set_attr(self, widget, *args):
        if self._update:
            if widget.size == 1:
                usd_values = self._python_type(widget.values()[0])
            else:
                usd_values = self._python_type(*widget.values())
            self._attr.Set(usd_values, self.frame)
            # self.changed.emit(usd_values)

    def on_time_sample_changes(self, status):
        self._time_sample_update = bool(status)


class ValueBase(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.size = ()
        self._attr = None
        self._frame = Usd.TimeCode.Default()
        self.is_array = False

        self.items_layout = QtWidgets.QVBoxLayout()

    @property
    def attr(self):
        return self._attr

    @attr.setter
    def attr(self, attr):
        self._attr = attr
        self.is_array = attr.GetTypeName().isArray

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if self.attr is None:
            return
        if self.is_time_sample():
            self._frame = Usd.TimeCode(value)
        else:
            self._frame = Usd.TimeCode.Default()

    @property
    def attr_value(self):
        return self._attr.Get(self._frame)

    def on_value_changed(self, *args):
        self.valueChanged.emit(self)

    def values(self):
        return []

    def is_time_sample(self):
        return bool(self.attr.GetNumTimeSamples())

    def construct(self):
        self._construct()
        self.set_value(self.attr_value)

        self.setLayout(self.items_layout)
        # self.layout().addItem(spacer)

    def _construct(self):
        pass

    def set_value(self, value):
        pass

    def update(self):
        self.set_value(self.attr_value)


class ValueBool(ValueBase):
    changed = QtCore.Signal(object)

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.items = []

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            item = QtWidgets.QCheckBox()
            layout.addWidget(item)
            self.items.append(item)
            item.stateChanged.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)

    def values(self):
        return [self.items[i].isChecked() for i in range(self.size)]

    def set_value(self, values):
        if is_scalar(values):
            values = [values]
        for i in range(self.size):
            self.items[i].setChecked(bool(values[i]))


class ValueInt(ValueBase):

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.items = []

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            item = QtWidgets.QSpinBox()
            item.setRange(-2147483647, 2147483647)
            layout.addWidget(item)
            self.items.append(item)
            item.valueChanged.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)

    def values(self):
        return [self.items[i].value() for i in range(self.size)]

    def set_value(self, value, *args):
        if is_scalar(value):
            value = [value]
        for i in range(self.size):
            self.items[i].setValue(value[i])


class ValueDouble(ValueInt):

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()

        for i in range(self.size):
            item = QtWidgets.QDoubleSpinBox()
            item.setRange(-2147483647.0, 2147483647.0)
            layout.addWidget(item)
            self.items.append(item)
            item.valueChanged.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)


class ValueString(ValueBase):

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.items = []

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            item = QtWidgets.QLineEdit()
            layout.addWidget(item)
            self.items.append(item)
            item.editingFinished.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)

    def values(self):
        return [self.items[i].text() for i in range(self.size)]

    def set_value(self, values):

        is_asset_path = isinstance(values, Sdf.AssetPath)

        if is_scalar(values) or is_asset_path:
            values = [values]

        if is_asset_path:
            for i in range(self.size):
                self.items[i].setText(values[i].path)
        else:
            for i in range(self.size):
                self.items[i].setText(str(values[i]))


class ValueAsset(ValueString):

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.items = []

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            resolve_cb = QtWidgets.QCheckBox("", self)
            resolve_cb.setToolTip("Resolve Path")
            layout.addWidget(resolve_cb)
            item = QtWidgets.QLineEdit()
            layout.addWidget(item)
            self.items.append(item)
            resolve_cb.stateChanged.connect(functools.partial(self.on_resolve, item))
            item.editingFinished.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)

    def on_resolve(self, item, checked):
        if checked:
            stage = self._attr.GetStage()
            resolved_text = stage.ResolveIdentifierToEditTarget(item.text())
            item.setText(resolved_text)
        else:
            self.set_value(self.attr_value)


class ValueToken(ValueBase):

    def __init__(self, size=1, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.items = []

    def _construct(self):
        tokens = self._attr.GetMetadata("allowedTokens") or []

        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            item = QtWidgets.QComboBox()
            item.setEditable(True)
            item.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
            item.addItems(list(tokens))
            item.setCompleter(QtWidgets.QCompleter(item.model()))
            item.lineEdit().textEdited.connect(self.show_dropdown_if_empty)

            layout.addWidget(item)
            self.items.append(item)
            item.lineEdit().editingFinished.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)

    def values(self):
        return [self.items[i].currentText() for i in range(self.size)]

    def set_value(self, values):
        if is_scalar(values):
            values = [values]

        for i in range(self.size):
            self.items[i].setCurrentText(str(values[i]))

    def show_dropdown_if_empty(self, text):
        if text == "":
            self.combo_box.showPopup()


class ValueColor(ValueBase):
    def __init__(self, size=1, alpha=False, parent=None):
        super().__init__(parent=parent)
        # clear_layout(self.layout())

        self.size = size
        self.items = []
        self.alpha = alpha

    def _construct(self):
        layout = QtWidgets.QHBoxLayout()
        for i in range(self.size):
            item = ColorWidget(alpha=self.alpha)
            layout.addWidget(item)
            self.items.append(item)
            item.valueChanged.connect(self.on_value_changed)

        self.items_layout.addLayout(layout)

    def values(self):
        return [item.rgba for item in self.items]

    def set_value(self, value, *args):
        for i in range(self.size):
            self.items[i].rgba = value


class ValueMatrix(ValueBase):

    def __init__(self, size, parent=None):
        super().__init__(parent=parent)
        self.size = size
        self.items = []

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
                item = QtWidgets.QDoubleSpinBox()
                item.setRange(-2147483647.0, 2147483647.0)
                r_layout.addWidget(item)
                row_items.append(item)
                item.valueChanged.connect(self.on_value_changed)

            matrix_layout.addLayout(r_layout)
            self.items.append(row_items)

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

                    item = QtWidgets.QDoubleSpinBox()
                    item.setRange(-2147483647.0, 2147483647.0)
                    row_items.append(item)
                    t_layout.addWidget(item)
                    item.valueChanged.connect(self.on_trs_value_changed)
                trs_layout.addLayout(t_layout)
                self.trs_items.append(row_items)

            self.matrix_widget.setHidden(True)
            self.trs_widget.setLayout(trs_layout)
            layout.addWidget(self.trs_widget)

        self.matrix_widget.setLayout(matrix_layout)
        layout.addWidget(self.matrix_widget)

        self.items_layout.addLayout(layout)

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
        matrix = compose_matrix(*values)

        self.set_value(matrix, update_trs=False)

    def values(self):
        values = []
        for r in range(self.size):
            for c in range(self.size):
                values.append(self.items[r][c].value())
        return values

    def trs_values(self):
        values = []
        for r in range(len(self.trs_items)):
            for c in range(len(self.trs_items[r])):
                values.append(self.trs_items[r][c].value())
        return values

    def set_value(self, value, update_trs=True, *args):
        for r in range(self.size):
            for c in range(self.size):
                self.items[r][c].setValue(value[r][c])

        if update_trs and self._trs_matrix:
            self.set_trs_value(value)

    def set_trs_value(self, value, *args):
        trs_values = decompose_matrix(value)
        for r in range(len(self.trs_items)):
            for c in range(len(trs_values[r])):
                self.trs_items[r][c].setValue(trs_values[r][c])
