from pxr import Sdf, Usd, Kind, Gf, UsdGeom

node = hou.pwd()
stage = node.editableStage()


asset_path = 'asset.usd'
asset_name = 'asset_name'
asset_prim_path = '/path'
asset_class_path = '/'

instanceable = True

def insert_asset_at(asset_prim_path='/', prim_type='Xform'):
    prim = stage.DefinePrim(asset_prim_path, prim_type)
    prim.GetReferences().AddInternalReference(original_prim.GetPath())
    # prim.GetReferences().AddReference(assetPath=asset_path)

    return prim


def inherit_from(child_prim, class_prim):
    child_prim = stage.GetPrimAtPath(asset_path)
    inherit = prim.GetInherits()
    inherit.AddInherit(class_prim.GetPath())


asset_prim_path = Sdf.Path(asset_prim_path)
asset_class_path = Sdf.Path(asset_class_path)

original_prim = stage.DefinePrim(f'{asset_prim_path}/{asset_name}', 'Xform')
original_prim.GetReferences().AddReference(assetPath=asset_path)

asset_class_prim = prim = insert_asset_at(asset_class_path.AppendPath(f'_class_{asset_name}'),
                                          'Xform')
asset_class_prim.SetSpecifier(Sdf.SpecifierDef)

for i in range(1, 10):
    prim = insert_asset_at(asset_prim_path.AppendPath(f'{asset_name}{i}'), 'Xform')

    prim.SetInstanceable(instanceable)

    model_API = Usd.ModelAPI(prim)
    model_API.SetKind(Kind.Tokens.component)

    inherit_from(prim, asset_class_prim)

    translation = Gf.Vec3d(i * 20, 0.0, 0.0)
    xformable = UsdGeom.Xformable(prim)
    xformable.AddTranslateOp().Set(value=translation)

# stage.RemovePrim(holder_prim.GetPath())
