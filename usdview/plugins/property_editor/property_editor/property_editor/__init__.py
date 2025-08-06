"""

    usdviewApi.dataModel - Usdview's active data model object.
    usdviewApi.stage - The current Usd.Stage.
    usdviewApi.frame - The current frame.
    usdviewApi.prim - The focus prim from the prim selection.
    usdviewApi.property - The focus property from the property selection.
    usdviewApi.spec - The currently selected Sdf.Spec from the Composition tab.
    usdviewApi.layer - The currently selected Sdf.Layer in the Composition tab.

https://github.com/PixarAnimationStudios/OpenUSD/blob/release/pxr/usdImaging/usdviewq/viewSettingsDataModel.py
https://openusd.org/release/tut_usdview_plugin.html

usdviewApi.dataModel- a full representation of usdview’s state. The majority of the data and functionality available to plugins is available through the data model.
stage - The current Usd.Stage object.
currentFrame - usdview’s current frame.
viewSettings - A collection of settings which only affect the viewport. Most of these settings are normally controlled using usdview’s ‘View’ menu. Some examples are listed below.
complexity - The scene’s subdivision complexity.
freeCamera - The camera object used when usdview is not viewing through a camera prim. Plugins can modify this camera to change the view.
renderMode - The mode used for rendering models (smooth-shaded, flat-shaded, wireframe, etc.).
selection - The current state of prim and property selections.
Common prim selection methods: getFocusPrim(), getPrims(), setPrim(prim), addPrim(prim), clearPrims()
Common property selection methods: getFocusProp(), getProps(), setProp(prop), addProp(prop), clearProps()
usdviewApi.qMainWindow - usdview’s Qt MainWindow object. It can be used as a parent for other Qt windows and dialogs, but it should not be used for any other purpose.
usdviewApi.PrintStatus(msg) - Prints a status message at the bottom of the usdview window.
GrabViewportShot()/GrabWindowShot() - Captures a screenshot of the viewport or the entire main window and returns it as a QImage.

"""

import functools

from PySide6 import QtWidgets
from pxr import Tf
from pxr.Usdviewq import plugin

from . import widgets


class PropertyEditor(plugin.PluginContainer):
    """ The class which registers the "Property Editor" plugin to usdview """

    Display_Name = "Property Editor"

    def registerPlugins(self, plugRegistry, usdviewApi):
        """
        This method is called after the container is discovered by Usdview,
        and should call 'registerCommandPlugin' one or more times on the
        plugRegistry to add commands to Usdview.

        Args:
            plugRegistry (`pxr.Usdviewq.plugin.PluginRegistry`):
                The USD-provided object that this plugin will be added to.

            usdviewApi (`pxr.Usdviewq.usdviewApi`):
                The USD-provided object that this plugin will be added to.
        """
        self.plugRegistry = plugRegistry
        self.usdviewApi = usdviewApi

    def configureView(self, plugRegistry, plugUIBuilder):
        """
        This method is called directly after 'registerPlugins' and can be
        used to add menus which invoke a plugin command using the plugUIBuilder.

        Args:
            plugRegistry (`pxr.Usdviewq.plugin.PluginRegistry`):
                The USD-provided object that this plugin will be added to.

            builder (:class:`pxr.Usdviewq.plugin.PluginUIBuilder`):
                The object responsible for adding menus to usdview.

        """
        self.plugUIBuilder = plugUIBuilder
        self.add_tap()

    def add_tap(self):
        mainwindow = self.usdviewApi.qMainWindow
        # model = self.usdviewApi.dataModel._selectionDataModel
        model = self.usdviewApi.dataModel

        tab_widgets = find_all_tab_widgets(mainwindow, "propertyInspector")
        if tab_widgets:
            tab_widget = tab_widgets[0]

            new_tab = QtWidgets.QWidget()
            new_tab.setObjectName("valueEditorTab")
            layout = QtWidgets.QVBoxLayout()
            new_tab.setLayout(layout)
            tab_widget.addTab(new_tab, "Value Editor")

            edit_widget = widgets.EditAttrWidget()
            new_tab.layout().addWidget(edit_widget)

            model.selection.signalPropSelectionChanged.connect(
                functools.partial(self.on_prop_selection_changes, edit_widget))

    def on_prop_selection_changes(self, edit_widget):

        model = self.usdviewApi.dataModel
        focus_prop = model.selection.getFocusProp()

        if focus_prop is None:
            focus_prim_path, focus_prop_name = (model.selection.getFocusComputedPropPath())
            if not focus_prim_path:
                return
            focus_prop_path = focus_prim_path.AppendProperty(focus_prop_name)
            focus_prop = model.stage.GetPropertyAtPath(focus_prop_path)

        else:
            focus_prim_path = focus_prop.GetPrimPath()
            focus_prop_name = focus_prop.GetName()

        print("-" * 50, focus_prop_name, "-" * 50)
        edit_widget.populate(prop=focus_prop, viewer=self.usdviewApi)


def find_all_tab_widgets(parent, name):
    tab_widgets = []

    def recursive_find(widget):
        for child in widget.children():
            if isinstance(child, QtWidgets.QTabWidget) and child.objectName() == name:
                tab_widgets.append(child)
            recursive_find(child)

    recursive_find(parent)
    return tab_widgets


# Register the new plugin
PluginContainerTfType = Tf.Type.Define(PropertyEditor)
