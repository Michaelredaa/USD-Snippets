# -*- coding: utf-8 -*-
"""
Documentation:
"""

import functools

from PySide6 import QtCore, QtWidgets
from pxr import Usd

from .custom import ListWidgetItem, WidgetRoleData, valueRoleData, TimeSamplesColor
from .item_widgets import VALUE_TYPE_MAPPING
from . import utils


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

        self.list_attr_widget.setHidden(True)
        self.list_rel_widget.setHidden(True)

    def populate(self, prop, viewer):
        self.viewer = viewer
        self.prop = prop

        if isinstance(prop, Usd.Attribute):
            self.list_attr_widget.setHidden(False)
            self.list_rel_widget.setHidden(True)
            self.draw_attr()
        else:
            self.list_attr_widget.setHidden(True)
            self.list_rel_widget.setHidden(False)
            self.draw_relationship()

    def draw_attr(self):
        self.keyframes = {}
        self.time_sample_cb = QtWidgets.QCheckBox("Update with timeSample")
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.key_btn = QtWidgets.QPushButton("Key")

        btn_layout = QtWidgets.QHBoxLayout(self)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.key_btn)

        self.list_attr_widget.reset()

        self.list_attr_widget._attr = self.prop
        self.list_attr_widget.viewer = self.viewer
        self.list_attr_widget.edit_attr_widget = self

        self.update_attribute_value()
        self.list_attr_widget.populate()

        self.list_attr_widget.valueChanged.connect(self.on_attr_value_changed)

        app_controller = self.viewer._UsdviewApi__appController
        app_controller._ui.frameSlider.sliderReleased.connect(
            functools.partial(self.update_attribute_value))

    def draw_relationship(self):

        self.list_rel_widget.rel = self.prop
        self.list_rel_widget.populate()

    def update_attribute_value(self):
        self.list_attr_widget.value = self.prop.Get(self.frame())

    def on_attr_value_changed(self, value_modifier, *args):
        value, modifier = value_modifier

        type_name = self.prop.GetTypeName()
        python_type, widget_factory = VALUE_TYPE_MAPPING.get(type_name, (None, None))

        values = value
        if len(values) == 1:
            values = value[0]

        if modifier == "lt+alt":
            self.keyframes[self.viewer.frame] = values
            for frame, t_values in self.keyframes.items():
                self.prop.Set(python_type(t_values), frame)

        elif modifier == "lt+alt+shift":
            self.keyframes = {}
            self.prop.Clear()
            self.prop.Set(python_type(values), self.frame())
            self.list_attr_widget._update = True

        else:
            self.prop.Set(python_type(values), self.frame())

    def frame(self):
        frame = self.viewer.frame if self.prop.GetNumTimeSamples() else Usd.TimeCode.Default()
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
        self.edit_attr_widget = None

        self.is_array = False

        self._time_sample_update = False
        self._keyframes = {}

        self.layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        self.layout.addWidget(self.list_widget)
        self.setLayout(self.layout)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if utils.is_scalar(value):
            value = [value]
        self._value = value

        item = self.list_widget.item(0)
        if item and self.is_time_sample(widget=item.data(WidgetRoleData)):
            self.set_item_data(value_modifier=[value, None], item=item)

    def populate(self):
        type_name = self._attr.GetTypeName()
        python_type, widget_factory = VALUE_TYPE_MAPPING.get(type_name, (None, None))
        if widget_factory is None:
            print(f"Unsupported type: {type_name}")
            return

        self.add_item(widget_factory())

    def add_item(self, widget):
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
            lambda value_modifier: self.set_item_data(value_modifier=value_modifier,
                                                      item=widget_item))
        widget_item.signal_wrapper.userRoleChanged.connect(self.on_value_changed)
        return widget_item

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
                widget.setStyleSheet("background-color: {};".format(TimeSamplesColor))
            return True
        else:
            widget.setStyleSheet("")
            return False


if __name__ == '__main__':
    print(__name__)
