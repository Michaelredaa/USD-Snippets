from pxr import Usd, Sdf, UsdGeom, Gf
import math

def set_cards_textures(prim: Usd.Prim, xpos: str, ypos: str, zpos: str, nxpos=None, nypos=None, nzpos=None, enable=True):
    """
    To set textures cards for given prim
    :param prim: The prim object
    :param xpos: The image path to set in positive x position
    :param ypos: The image path to set in positive y position
    :param zpos: The image path to set in positive z position
    :param nxpos: The image path to set in negative x position
    :param nypos: The image path to set in negative y position
    :param nzpos: The image path to set in negative z position
    :param enable: To enable the draw mode in the viewport
    :return:
    """

    modelAPI: UsdGeom.ModelAPI = UsdGeom.ModelAPI(prim)

    if not modelAPI:
        return "Please select Model prim"

    modelAPI.CreateModelCardTextureXPosAttr(xpos)
    modelAPI.CreateModelCardTextureYPosAttr(ypos)
    modelAPI.CreateModelCardTextureZPosAttr(zpos)

    if nxpos:
        modelAPI.CreateModelCardTextureXNegAttr(xpos)

    if nypos:
        modelAPI.CreateModelCardTextureYNegAttr(xpos)

    if nzpos:
        modelAPI.CreateModelCardTextureZNegAttr(xpos)

    if enable:
        modelAPI.CreateModelDrawModeAttr(UsdGeom.Tokens.cards)
        modelAPI.CreateModelApplyDrawModeAttr(True)


def create_projection_cameras(prim: Usd.Prim, cameras_root='/cameras'):

    stage:           Usd.Stage          = prim.GetStage()

    # time_code = Usd.TimeCode.Default()
    # bbox_cache = UsdGeom.BBoxCache(time_code, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
    #                                useExtentsHint=True, ignoreVisibility=False)
                                    
    # bbox = bbox_cache.ComputeWorldBound(prim)
    # size = bbox.GetBox().GetSize()
    # center = bbox.GetBox().GetMidpoint()
    
    prim_imageable:  UsdGeom.Imageable  = UsdGeom.Imageable(prim)
    bound:           Gf.BBox3d          = prim_imageable.ComputeWorldBound(Usd.TimeCode.Default(), UsdGeom.Tokens.default_)
    bbox_range:      Gf.Range3d         = bound.ComputeAlignedBox()
    size:            Gf.Vec3d           = bbox_range.GetSize()
    center:          Gf.Vec3d           = bbox_range.GetMidpoint()


    # XPOS :: Front
    cam_pos_x:       Gf.Vec3d           = center + Gf.Vec3d(size.GetLength() * 1, 0, 0)
    xh_aperature:    float              = (size[1] * 10) + math.atan2(2 * size[1],  math.pi)
    xv_aperature:    float              = (size[2] * 10) + math.atan2(2 * size[2], math.pi)
    xpos_path:       Sdf.Path           = Sdf.Path(cameras_root).AppendChild("XPOS")
    xpos_camera:     UsdGeom.Camera     = UsdGeom.Camera.Define(stage, xpos_path)

    xpos_camera.AddTranslateOp().Set(cam_pos_x)
    xpos_camera.AddRotateXYZOp().Set(Gf.Vec3f(90, 0, 90))
    xpos_camera.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
    xpos_camera.CreateHorizontalApertureAttr(xh_aperature)
    xpos_camera.CreateVerticalApertureAttr(xv_aperature)

    # ZPOS :: Side
    cam_pos_z:       Gf.Vec3d           = center + Gf.Vec3d(0, 0, size.GetLength() * 10)
    zh_aperature:    float              = (size[0] * 10) + math.atan2(2 * size[0], math.pi)
    zv_aperature:    float              = (size[1] * 10) + math.atan2(2 * size[1],  math.pi)
    zpos_path:       Sdf.Path           = Sdf.Path(cameras_root).AppendChild("ZPOS")
    zpos_camera:     UsdGeom.Camera     = UsdGeom.Camera.Define(stage, zpos_path)

    zpos_camera.AddTranslateOp().Set(cam_pos_z)
    zpos_camera.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
    zpos_camera.CreateHorizontalApertureAttr(zh_aperature)
    zpos_camera.CreateVerticalApertureAttr(zv_aperature)

    # YPOS :: Top
    cam_pos_y:       Gf.Vec3d           = center + Gf.Vec3d(0, size.GetLength() * 20, 0)
    yh_aperature:    float              = (size[0] * 10) + math.atan2(2 * size[0], math.pi)
    yv_aperature:    float              = (size[2] * 10) + math.atan2(2 * size[2],  math.pi)
    ypos_path:       Sdf.Path           = Sdf.Path(cameras_root).AppendChild("YPOS")
    ypos_camera:     UsdGeom.Camera     = UsdGeom.Camera.Define(stage, ypos_path)

    ypos_camera.AddTranslateOp().Set(cam_pos_y)
    ypos_camera.AddRotateXYZOp().Set(Gf.Vec3f(90, 0, 180))
    ypos_camera.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
    ypos_camera.CreateHorizontalApertureAttr(yh_aperature)
    ypos_camera.CreateVerticalApertureAttr(yv_aperature)



