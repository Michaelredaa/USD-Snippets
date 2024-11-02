# -*- coding: utf-8 -*-
"""
Documentation:
"""
from typing import List

from pxr import Usd, Sdf, UsdGeom, Gf

import hou


def get_points_data(node: hou.SopNode):
    data = {
        "position": [],
        "rotation": [],
        "pscale": [],
        "variant": [],
    }
    geometry = node.geometry()
    for p in geometry.points():
        data["position"].append(p.position())

        if geometry.findPointAttrib("rotation"):
            data["rotation"].append(p.attribValue("rotation"))

        if geometry.findPointAttrib("pscale"):
            data["pscale"].append(p.attribValue("pscale"))

        data["variant"].append(p.attribValue("variant"))

    return data


def explore_variants(prim: Usd.Prim, destination_prim: Sdf.Path, variantset_name="model") -> List[Usd.Prim]:
    stage = prim.GetStage()
    variantset = prim.GetVariantSet(variantset_name)
    variant_names = variantset.GetVariantNames()

    variant_prims = []
    for name in variant_names:
        variant_prim = stage.DefinePrim(destination_prim.AppendChild(name), "Xform")
        variant_prim.GetReferences().AddInternalReference(prim.GetPath())
        variant_prim.GetVariantSet(variantset_name).SetVariantSelection(name)
        variant_prims.append(variant_prim)

    return variant_prims


def create_point_instancer(
        assets_prim: Usd.Prim,
        instancer_path: Sdf.Path,
        indices: List[int],
        positions=None,
        orientations=None,
        scales=None):
    if scales is None:
        scales = []
    if orientations is None:
        orientations = []
    if positions is None:
        positions = []

    prototypes = []

    stage = assets_prim.GetStage()

    instancer_prim = UsdGeom.PointInstancer.Define(stage, instancer_path)
    prototypes_path = instancer_prim.GetPath().AppendChild('prototypes')
    prototypes_prim = UsdGeom.Scope.Define(stage, prototypes_path)

    variant_prims = explore_variants(assets_prim, prototypes_path)

    instancer_prim.GetProtoIndicesAttr()
    prototypes.insert(0, prototypes_path)
    prototypes.extend([p.GetPath() for p in variant_prims])

    instancer_prim.CreatePrototypesRel().SetTargets(prototypes)

    positions_array = []
    orientations_array = []
    scales_array = []

    for p in positions:
        positions_array.append(Gf.Vec3f(p[0], p[1], p[2]))

    for p in scales:
        scales_array.append(Gf.Vec3f(p, p, p))

    for p in orientations:
        rot = Gf.Rotation()
        roty = Gf.Rotation(Gf.Vec3d(0, 1, 0), p[1])
        rotx = Gf.Rotation(Gf.Vec3d(1, 0, 0), p[0])
        rotz = Gf.Rotation(Gf.Vec3d(0, 0, 1), p[2])
        rot = roty * rotx * rotz
        r = rot.GetQuaternion().GetReal()
        img = rot.GetQuaternion().GetImaginary()

        q = Gf.Quath(r, img[0], img[1], img[2])
        orientations_array.append(q)

    if positions_array:
        instancer_prim.CreatePositionsAttr(positions_array)

    if orientations_array:
        instancer_prim.CreateOrientationsAttr(orientations_array)

    if scales_array:
        instancer_prim.CreateScalesAttr(scales_array)

    instancer_prim.CreateProtoIndicesAttr(indices)
