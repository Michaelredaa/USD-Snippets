# -*- coding: utf-8 -*-
"""
Documentation:
"""

import functools
import traceback
import math

from collections.abc import Iterable

from PySide6 import QtCore, QtGui, QtWidgets

WidgetRoleData = QtCore.Qt.UserRole + 10
valueRoleData = QtCore.Qt.UserRole + 20

KeyFrameColor = "#468C46"
TimeSamplesColor = "#40806D"




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
        return self.isChecked()

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

        self.valueChanged.connect(lambda: self.changed.emit(self.value()))

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
        self.setSingleStep(0.1)
        self.setRange(-2147483647.0, 2147483647.0)

        self.valueChanged.connect(lambda: self.changed.emit(self.value()))

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






if __name__ == '__main__':
    print(__name__)
