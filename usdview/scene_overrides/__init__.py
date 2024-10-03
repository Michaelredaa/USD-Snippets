"""

    usdviewApi.dataModel - Usdview's active data model object.
    usdviewApi.stage - The current Usd.Stage.
    usdviewApi.frame - The current frame.
    usdviewApi.prim - The focus prim from the prim selection.
    usdviewApi.property - The focus property from the property selection.
    usdviewApi.spec - The currently selected Sdf.Spec from the Composition tab.
    usdviewApi.layer - The currently selected Sdf.Layer in the Composition tab.

https://github.com/PixarAnimationStudios/OpenUSD/blob/release/pxr/usdImaging/usdviewq/viewSettingsDataModel.py

"""

import contextlib
import functools

from pxr.Usdviewq.qt import QtCore, QtGui, QtWidgets
from pxr import Sdf, Tf, Usd, UsdGeom
from pxr.Usdviewq import plugin, appController, Utils


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

        create_camera_action.triggered.connect(functools.partial(self.on_create_camera))
        list_camera_action.triggered.connect(functools.partial(self.on_list_cameras))
        save_overrides_action.triggered.connect(functools.partial(self.on_save_overrides))

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
    path = Sdf.Path("{}/{}".format(CAMERAS_ROOT, "camera"+str(len(children)+1)))
    path = path.GetPrimPath()
    return path


def create_prim(stage, prim_path, prim_type="Xform"):
    prim = stage.DefinePrim(prim_path, prim_type)

    return prim




# We load the PluginContainer using libplug so it needs to be a defined Tf.Type.
PluginContainerTfType = Tf.Type.Define(SceneOverrides)
