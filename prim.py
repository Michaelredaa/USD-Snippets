from pxr import Sdf, Usd, UsdShade, UsdGeom

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
    
