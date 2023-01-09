from pxr import UsdShade
node = hou.pwd()
stage = node.editableStage()


import re
from pxr import UsdShade, UsdGeom

node = hou.pwd()
stage = node.editableStage()


def binds_material(new_stage, prim_path, mtl_path):
    # get material as pxr.UsdShade.Material
    mtl_ref_prim = UsdShade.Material.Define(new_stage, mtl_path)
    UsdShade.MaterialBindingAPI(new_stage.GetPrimAtPath(str(prim_path))).Bind(mtl_ref_prim)
    

for prim in stage.Traverse():
    if not prim.GetTypeName() == 'GeomSubset':
        continue
    subset_name = prim.GetName()
    prim.GetAttribute("familyName").Set("materialBind")
    
    material_prim = UsdShade.Material.Define(stage, f'/ASSET/mtl/{subset_name}')
    binds_material(stage, prim.GetPath(), material_prim.GetPath())
