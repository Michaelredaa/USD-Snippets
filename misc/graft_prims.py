from pxr import Usd, Sdf, Vt, UsdShade

node = hou.pwd()

def graft_prim(source_stage, destination_stage, source_path, destination_path):
    """
    Grafts a prim from source_stage at source_path to destination_stage at destination_path.
    This includes copying all properties, variant sets, and material bindings.
    """

    source_prim = source_stage.GetPrimAtPath(source_path)
    for prim in Usd.PrimRange(source_prim):
        dest_path = Sdf.Path(str(prim.GetPath()).replace(str(source_path), str(destination_path)))

        new_prim = destination_stage.DefinePrim(dest_path, prim.GetTypeName())
        for prop in prim.GetAuthoredProperties():
            if isinstance(prop, Usd.Attribute):
                new_attr = new_prim.CreateAttribute(prop.GetName(), prop.GetTypeName())
                if prop.Get():
                    new_attr.Set(prop.Get())
                for time in prop.GetTimeSamples():
                    new_attr.Set(prop.Get(time), time)

                for metadata_key in prop.GetAllAuthoredMetadata():
                    new_attr.SetMetadata(metadata_key, prop.GetMetadata(metadata_key))

            elif isinstance(prop, Usd.Relationship):
                new_rel = new_prim.CreateRelationship(prop.GetName())
                new_rel.SetTargets(prop.GetTargets())

        if prim.HasVariantSets():
            source_variant_sets = prim.GetVariantSets()
            for variant_set_name in source_variant_sets.GetNames():
                source_variant_set = source_variant_sets.GetVariantSet(variant_set_name)

                new_variant_set = new_prim.GetVariantSets().AddVariantSet(variant_set_name)
                for variant_name in source_variant_set.GetVariantNames():
                    new_variant_set.AddVariant(variant_name)
                    new_variant_set.SetVariantSelection(source_variant_set.GetVariantSelection())

        for key in prim.GetAllAuthoredMetadata():
            if key not in ("specifier", "typeName", "variantSets"):
                value = prim.GetMetadata(key)
                new_prim.SetMetadata(key, value)


        # Get the material bound to the source prim.
        binding_api = UsdShade.MaterialBindingAPI(prim)
    
        for purpose in [UsdShade.Tokens.full, UsdShade.Tokens.preview]:
            material, relationships = binding_api.ComputeBoundMaterial(purpose)
    
            if material:
                material_path = material.GetPath()
                if material_path.HasPrefix(source_path):
                    new_material_path = Sdf.Path(str(material_path).replace(str(source_path), str(destination_path)))
                    new_material_prim = destination_stage.GetPrimAtPath(new_material_path)
                    if new_material_prim:
                        new_material = UsdShade.Material(new_material_prim)
    
                        new_binding_api = UsdShade.MaterialBindingAPI(new_prim)
                        new_binding_api.Bind(
                            new_material,
                            materialPurpose=purpose,
                            bindingStrength=binding_api.GetMaterialBindingStrength(relationships)
                        )


def inherit_from(ref_prim, class_prim):
    class_prim.SetSpecifier(Sdf.SpecifierClass)

    inherit = ref_prim.GetInherits()
    inherit.AddInherit(class_prim.GetPath())




source_stage = node.input(0).stage()
destination_stage = node.editableStage()

instanceable = True
source_path = Sdf.Path("/pig")
class_root_path = Sdf.Path("/more")

asset_name = source_path.name
destination_path = class_root_path.AppendPath(f'__class__{asset_name}')
graft_prim(source_stage, destination_stage, source_path, destination_path)


asset_prim = destination_stage.GetPrimAtPath(source_path)
class_prim = destination_stage.GetPrimAtPath(destination_path)
inherit_from(asset_prim, class_prim)

asset_prim.SetInstanceable(instanceable)
