from pxr import Sdf, Usd, UsdShade, UsdGeom


def get_bound_geoms(material_prim: Usd.Prim):
    """
    To get all bound geom with specific material prim

    @parm prim: pxr.Prim
    return list(pxr.Prim)
    """

    prim_type = material_prim.GetTypeName()

    if prim_type != 'Material':
        return []

    material_path = material_prim.GetPath()
    stage = material_prim.GetStage()

    geom_prims = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Imageable):
            continue

        material, material_rel = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(
            UsdShade.Tokens.full)
        # material_rel = prim.GetRelationship('material:binding')

        if not material_rel.IsValid():
            continue

        if material_path in material_rel.GetTargets():
            geom_prims.append(prim)

    return geom_prims


def delete_prim(prim: Usd.Prim):
    """
    To detete prim from usd layers
    https://lucascheller.github.io/VFX-UsdSurvivalGuide/production/concepts.html?highlight=Sdf.ChangeBlock()%3A#delaying-change-notifications-with-the-sdfchangeblock
    """
    for prim_spec in prim.GetPrimStack():
        with Sdf.ChangeBlock():
            edit = Sdf.BatchNamespaceEdit()
            edit.Add(prim_spec.path, Sdf.Path.emptyPath)

        if not prim_spec.layer.Apply(edit):
            raise Exception("Failed to apply layer edit!")
        prim_spec.layer.Save()
