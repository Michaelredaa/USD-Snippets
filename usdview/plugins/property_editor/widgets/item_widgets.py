# -*- coding: utf-8 -*-
"""
Documentation:
"""
import functools

from PySide6 import QtCore, QtGui, QtWidgets
from pxr import Sdf, Gf, Usd

from . import utils

from . custom import SpinBox, DoubleSpinBox, CheckBox, LineEdit, LineEditTokens, ColorFiled

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


Widget_Types = {
    "int": SpinBox,
    "float": DoubleSpinBox,
    "bool": CheckBox,
    "string": LineEdit
}


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
        self._values = utils.compose_matrix(*values)  # matrix
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
        trs_values = utils.decompose_matrix(self._values)
        for r in range(len(self.trs_items)):
            for c in range(len(trs_values[r])):
                self.trs_items[r][c].setValue(trs_values[r][c])






if __name__ == '__main__':
    print(__name__)
