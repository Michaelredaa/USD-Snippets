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



def create_bbox_prim(prim: Usd.Prim, box_path: str) -> UsdGeom.Mesh:
    """Create a box the represent the bbox for prim"""

    stage = prim.GetStage()
    bbox = get_bbox_with_xform(prim)

    """
    https://openusd.org/release/api/class_gf_range3d.html#af3e88ddd9c61229ce81086a4bdac1bc8
    Returns the ith corner of the range, in the following order: LDB, RDB, LUB, RUB, LDF, RDF, LUF, RUF.
    Where L/R is left/right, D/U is down/up, and B/F is back/front.
    # 0 1 2 3 5 4 6 7
    """

    face_vertex_indices = [
        [0, 1, 3, 2],
        [5, 4, 6, 7],
        [7, 6, 2, 3],
        [4, 5, 1, 0],
        [4, 0, 2, 6],
        [1, 5, 7, 3]
    ]

    face_vertex_indices_flat = [idx for face in face_vertex_indices for idx in face]
    face_vertex_counts = [4] * len(face_vertex_indices)

    points = []
    for i in range(8):
        corner = bbox.GetCorner(i)
        points.append(corner)

    mesh = UsdGeom.Mesh.Define(stage, box_path)

    mesh.CreateFaceVertexCountsAttr(face_vertex_counts)
    mesh.CreateFaceVertexIndicesAttr(face_vertex_indices_flat)
    mesh.CreatePointsAttr(points)

    mesh.GetSubdivisionSchemeAttr().Set("none")

    return mesh
