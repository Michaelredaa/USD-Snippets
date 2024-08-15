from pxr import Sdf, Usd, UsdShade, UsdGeom, Gf

def delete_prim(prim: Usd.Prim):
    """
    To delete prim from usd layers
    https://lucascheller.github.io/VFX-UsdSurvivalGuide/production/concepts.html?highlight=Sdf.ChangeBlock()%3A#delaying-change-notifications-with-the-sdfchangeblock
    """
    for prim_spec in prim.GetPrimStack():
        with Sdf.ChangeBlock():
            edit = Sdf.BatchNamespaceEdit()
            edit.Add(prim_spec.path, Sdf.Path.emptyPath)

        if not prim_spec.layer.Apply(edit):
            raise Exception("Failed to apply layer edit!")
        prim_spec.layer.Save()


def get_kind(prim: Usd.Prim):
    return Usd.ModelAPI(prim).GetKind()


def get_bbox(prim: Usd.Prim) -> Gf.BBox3d:
    """To get the bbox for the prim"""
    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                                   useExtentsHint=False, ignoreVisibility=False)
    bbox = bbox_cache.ComputeWorldBound(prim)

    return bbox.GetBox()


def get_resultant_xform_scale(prim: Usd.Prim) -> tuple:
    """
    Get the resultant scale for all xfromOp on the prim
    :return:
    """

    xform = UsdGeom.Xform(prim)
    sx = sy = sz = 1
    for op in xform.GetOrderedXformOps():
        op_value = op.Get()
        if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
            if not isinstance(op_value, Gf.Matrix4d):
                continue

            sx *= op_value[0][0]
            sy *= op_value[1][1]
            sz *= op_value[2][2]

    return sx, sy, sz


def get_bbox_with_xform(prim: Usd.Prim):
    """To get the bbox for  the prim and consider the xforms for the prim"""

    bbox = get_bbox(prim)
    sx, sy, sz = get_resultant_xform_scale(prim)

    bmin = bbox.GetMin()
    bmax = bbox.GetMax()

    bmin = Gf.Vec3d(bmin[0]*sx, bmin[1]*sy, bmin[2]*sz)
    bmax = Gf.Vec3d(bmax[0]*sx, bmax[1]*sy, bmax[2]*sz)

    return Gf.BBox3d(Gf.Range3d(bmin, bmax)).GetBox()
