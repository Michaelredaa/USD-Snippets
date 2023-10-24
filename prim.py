from pxr import UsdShade


def get_bound_materials(prim):
  """
  @parm prim: pxr.Prim
  To get the bound materials on given prim
  return list(pxr.UsdShade.Material)
  """
  materials, relationships = UsdShade.MaterialBindingAPI.ComputeBoundMaterials([prim])

  return materials
