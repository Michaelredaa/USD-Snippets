from pxr import UsdShade


def get_bound_materials(prim):
  """
  To get the bound materials on given prim

  @parm prim: pxr.Prim
  return list(pxr.UsdShade.Material)
  """
  materials, relationships = UsdShade.MaterialBindingAPI.ComputeBoundMaterials([prim])

  return materials


def get_bound_geoms(material_prim):
    """
    To get all bound geom with specific material prim

    @parm prim: pxr.Prim
    return list(pxr.Prim)
    """
        
    prim_type = material_prim.GetTypeName()
    
    if prim_type != 'Material':
        return []
    
    material_path = selected_prim.GetPath()
    stage = selected_prim.GetStage()
    
    geom_prims = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Imageable):
            continue
            
        material_rel = prim.GetRelationship('material:binding')
        
        if not material_rel.IsValid():
            continue
        
        if material_path in material_rel.GetTargets():
            geom_prims.append(prim)
            
    return geom_prims
