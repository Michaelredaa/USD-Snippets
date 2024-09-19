try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt, Kind


def get_bbox_cache(use_extents_hint=False, ignore_visibility=False):
    return UsdGeom.BBoxCache(
        time_code,
        ["default", "render", "proxy", "guide"],
        useExtentsHint=use_extents_hint,
        ignoreVisibility=ignore_visibility
    )


def get_frustum(camera_prim: Usd.Prim, frame: float, padding=1.0) -> Gf.Frustum:
    camera_type_api = UsdGeom.Camera(camera_prim)
    camera_api = camera_type_api.GetCamera(frame)
    frustum = camera_api.frustum
    window = frustum.GetWindow() * padding
    frustum.SetWindow(window)
    return frustum


def draw_frustum(camera_prim: Usd.Prim, frame: float, padding=1.0) -> UsdGeom.Mesh:
    frustum = get_frustum(camera_prim, frame, padding)
    corners = frustum.ComputeCorners()
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
    for i in range(len(corners)):
        points.append(corners[i])

    mesh = UsdGeom.Mesh.Define(stage, "/frustum")
    mesh.CreateFaceVertexCountsAttr(face_vertex_counts)
    mesh.CreateFaceVertexIndicesAttr(face_vertex_indices_flat)
    mesh.CreatePointsAttr(points)
    mesh.GetSubdivisionSchemeAttr().Set("none")

    opacity_attr = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("displayOpacity", Sdf.ValueTypeNames.Float)
    opacity_attr.Set([0.5] * 3)

    return mesh


def camera_cull(stage: Usd.Stage, camera_prim: Usd.Prim, start_root: Usd.Prim = None,
                frame: float = 1.0, padding: float = 1.0,
                inclusion_mode: Literal["bbox", "position"] = "bbox",
                prune_mode: Literal["visibility", "activate"] = "activate",
                use_extents_hint: bool = False
                ):
    if start_root is None:
        start_root = stage.GetPseudoRoot()

    frustum = get_frustum(camera_prim, frame, padding)
    bbox_cache = get_bbox_cache(use_extents_hint=use_extents_hint)

    predicate = Usd.PrimIsActive & Usd.PrimIsDefined & Usd.PrimIsLoaded & Usd.PrimIsModel & Usd.PrimIsGroup

    it = iter(Usd.PrimRange(start_root, predicate=predicate))
    for prim in it:
        if prim.IsA(UsdGeom.PointInstancer):
            pointinstancer_api = UsdGeom.PointInstancer(prim)
            protoIndices_attr = pointinstancer_api.GetProtoIndicesAttr()
            if not protoIndices_attr.HasValue():
                print("Skipping... pointinstancer have not any values: {}".format(prim.GetPath()))
                continue

            if inclusion_mode == "bbox":
                protoIndices_values = protoIndices_attr.Get(frame)
                bboxes = bbox_cache.ComputePointInstanceWorldBounds(pointinstancer_api, range(len(protoIndices_values)))
                mask = np.array([frustum.Intersects(bbox) for bbox in bboxes])

            elif inclusion_mode == "position":
                positions_attr = pointinstancer_api.GetPositionsAttr()
                positions_values = positions_attr.Get(frame)
                mask = np.array([frustum.Intersects(tuple(pos)) for pos in positions_values])
            else:
                continue

            deactivate_ids = np.where(mask == 0)[0]
            pointinstancer_api.InvisIds(Vt.Int64Array.FromNumpy(deactivate_ids), frame)

            it.PruneChildren()

        if Usd.ModelAPI(prim).GetKind() == Kind.Tokens.component:
            is_inside = False
            if inclusion_mode == "bbox":
                box = bbox_cache.ComputeWorldBound(prim)
                is_inside = frustum.Intersects(box)

            elif inclusion_mode == "position":
                box = bbox_cache.ComputeWorldBound(prim)
                pos = box.ComputeCentroid()
                is_inside = frustum.Intersects(pos)

            if prune_mode == "activate":
                prim.SetActive(is_inside)

            elif prune_mode == "visibility":
                prim.GetAttribute("visibility").Set(is_inside)

            it.PruneChildren()


if __name__ == "__main__":
    import hou
    node = hou.pwd()
    stage = node.editableStage()

    padding = 1.1

    time_code = hou.frame()
    camera_prim = stage.GetPrimAtPath("/cameras/camera1")
    camera_cull(stage, camera_prim)
