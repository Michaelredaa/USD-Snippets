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

import contextlib
import functools

from PySide2 import QtCore, QtGui, QtWidgets
from pxr import Sdf, Tf, Usd, UsdGeom
from pxr.Usdviewq import plugin, appController, Utils

from . import widgets

CAMERAS_ROOT = "/cameras"



class SceneOverrides(plugin.PluginContainer):
    """ The class which registers the "scence overrides" plugin to usdview """

    Display_Name = "Scene Overrides"

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
        self.set_menus()
        self.add_tap()

    def deferredImport(self, moduleName):
        """Return a DeferredImport object which can be used to lazy load
        functions when they are invoked for the first time.
        """
        ...

    def get_all_cameras(self):
        return Utils._GetAllPrimsOfType(self.usdviewApi.dataModel.stage, Tf.Type.Find(UsdGeom.Camera))

    def set_camera(self, cam):
        viewSettings = self.usdviewApi.dataModel.viewSettings
        viewSettings.cameraPath = cam.GetPath()

    def set_menus(self):
        menu_bar = self.plugUIBuilder._mainWindow.menuBar()
        menu = menu_bar.addMenu(self.Display_Name)
        create_camera_action = menu.addAction("Camera Form View")
        list_camera_action = menu.addAction("List Cameras")
        save_overrides_action = menu.addAction("Save Overrides")
        save_snap_action = menu.addAction("Save Snap")

        create_camera_action.triggered.connect(functools.partial(self.on_create_camera))
        list_camera_action.triggered.connect(functools.partial(self.on_list_cameras))
        save_overrides_action.triggered.connect(functools.partial(self.on_save_overrides))
        save_snap_action.triggered.connect(functools.partial(self.on_save_snap))

    def on_create_camera(self):
        stage = self.usdviewApi.dataModel.stage
        print(dir(self.usdviewApi.dataModel))
        context = Usd.EditContext(stage, stage.GetSessionLayer())

        with context:
            camera_api = UsdGeom.Camera.Define(stage, predict_camera_name(stage))
            camera_api.SetFromCamera(self.usdviewApi.currentGfCamera)

        print("on_create_camera")

    def on_list_cameras(self):
        win = CamerasViewWidget(self.get_all_cameras(), plugin=self, parent=self.usdviewApi.qMainWindow)

        win.show()

        print("on_list_cameras")

    def add_tap(self):
        mainwindow = self.usdviewApi.qMainWindow
        # model = self.usdviewApi.dataModel._selectionDataModel
        model = self.usdviewApi.dataModel

        tab_widgets = find_all_tab_widgets(mainwindow, "propertyInspector")
        if tab_widgets:
            tab_widget = tab_widgets[0]

            new_tab = QtWidgets.QWidget()
            new_tab.setObjectName("newTab")
            layout = QtWidgets.QVBoxLayout()
            new_tab.setLayout(layout)
            tab_widget.addTab(new_tab, "New Tab")

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


    def on_save_overrides(self):
        self._save_session("foo.usda")
        print("on_save_overrides")

    def _save_session(self, layer_path):
        stage = self.usdviewApi.dataModel.stage

        temp_stage = Usd.Stage.CreateNew(layer_path)
        temp_stage.GetRootLayer().TransferContent(stage.GetSessionLayer())
        temp_stage.GetRootLayer().subLayerPaths.append(stage.GetRootLayer().identifier)

        temp_stage.SetDefaultPrim(stage.GetDefaultPrim())

        temp_stage.Save()

    def on_save_snap(self):
        image = self.usdviewApi.GrabViewportShot()
        # image = self.usdviewApi.GrabWindowShot()
        image.save("output_image.png", "PNG")

        print("on_save_snap")


class CamerasViewWidget(QtWidgets.QWidget):
    PrimRoleData = QtCore.Qt.UserRole + 10

    def __init__(self, cameras, plugin=None, parent=None):
        super(CamerasViewWidget, self).__init__(parent=parent)

        self.cameras = cameras
        self.plugin = plugin
        self.setWindowTitle('Cameras list')
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(300, 200)

        layout = QtWidgets.QVBoxLayout()
        self.list_view = QtWidgets.QListView()
        self.model = QtGui.QStandardItemModel()
        self.list_view.setModel(self.model)

        layout.addWidget(self.list_view)
        self.setLayout(layout)
        self.list_view.setMouseTracking(True)

        self.populate()

        # self.list_view.clicked.connect(self.on_item_selected)
        self.list_view.doubleClicked.connect(self.on_item_selected)

    def populate(self):
        for cam in self.cameras:
            item = QtGui.QStandardItem(cam.GetName())
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            item.setToolTip(cam.GetPath().pathString)
            item.setData(cam, self.PrimRoleData)

            self.model.appendRow(item)

    def on_item_selected(self, index):
        camera_prim = index.data(self.PrimRoleData)

        self.plugin.set_camera(camera_prim)
        # Print the original data
        print(f"Selected Meme Data: {camera_prim}")



def predict_camera_name(stage):
    cameras_prim = create_prim(stage, CAMERAS_ROOT)
    # cameras_prim = UsdGeom.Xform.Define(stage, CAMERAS_ROOT)
    children = cameras_prim.GetPrim().GetChildrenNames()
    path = Sdf.Path("{}/{}".format(CAMERAS_ROOT, "camera" + str(len(children) + 1)))
    path = path.GetPrimPath()
    return path


def create_prim(stage, prim_path, prim_type="Xform"):
    prim = stage.DefinePrim(prim_path, prim_type)

    return prim


def find_all_tab_widgets(parent, name):
    tab_widgets = []

    def recursive_find(widget):
        for child in widget.children():
            if isinstance(child, QtWidgets.QTabWidget) and child.objectName() == name:
                tab_widgets.append(child)
            recursive_find(child)

    recursive_find(parent)
    return tab_widgets


# We load the PluginContainer using libplug so it needs to be a defined Tf.Type.
PluginContainerTfType = Tf.Type.Define(SceneOverrides)
