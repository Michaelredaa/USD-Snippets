from pxr import Usd, UsdGeom, Sdf, Gf, Vt
import hou

def find_instanceable_references(stage):
    grouped_instances = {}

    for prim in stage.Traverse():
        if prim.IsInstanceable():
            asset_path = None
            
            prim_stack = prim.GetPrimStack()
            if prim_stack and prim_stack[0].referenceList.prependedItems:
                asset_path = prim_stack[0].referenceList.prependedItems[0].assetPath
            
            if not asset_path:
                asset_path = "internal_or_anonymous_reference"
                
            if asset_path not in grouped_instances:
                grouped_instances[asset_path] = []
                
            grouped_instances[asset_path].append(prim.GetPath())
            
    return grouped_instances

def convert_native_instances_to_point_instancer(stage, prim_paths, instancer_path):
    if not prim_paths:
        print("No primitive paths provided.")
        return

    first_prim = stage.GetPrimAtPath(prim_paths[0])
    if not first_prim:
        print(f"Base prim not found: {prim_paths[0]}")
        return

    positions = []
    orientations = []
    scales = []
    proto_indices = []

    for path in prim_paths:
        prim = stage.GetPrimAtPath(path)
        if not prim.IsValid():
            continue
            
        xformable = UsdGeom.Xformable(prim)
        time = Usd.TimeCode.Default()
        
        local_matrix = xformable.GetLocalTransformation(time)
        transform = Gf.Transform()
        transform.SetMatrix(local_matrix)
        
        translation = transform.GetTranslation()
        rotation = transform.GetRotation().GetQuat()
        scale = transform.GetScale()
        
        positions.append(Gf.Vec3f(translation))
        orientations.append(Gf.Quath(Gf.Quatf(rotation)))
        scales.append(Gf.Vec3f(scale))
        
        proto_indices.append(0)

    instancer = UsdGeom.PointInstancer.Define(stage, instancer_path)
    
    proto_scope_path = instancer_path.AppendChild("Prototypes")
    UsdGeom.Scope.Define(stage, proto_scope_path)
    
    proto_prim_path = proto_scope_path.AppendChild(first_prim.GetName())
    proto_prim = stage.DefinePrim(proto_prim_path)
    
    if first_prim.GetPrimStack():
        for ref in first_prim.GetPrimStack()[0].referenceList.prependedItems:
            proto_prim.GetReferences().AddReference(ref)

    instancer.CreatePositionsAttr(Vt.Vec3fArray(positions))
    instancer.CreateOrientationsAttr(Vt.QuathArray(orientations))
    instancer.CreateScalesAttr(Vt.Vec3fArray(scales))
    instancer.CreateProtoIndicesAttr(Vt.IntArray(proto_indices))
    
    proto_rel = instancer.CreatePrototypesRel()
    proto_rel.AddTarget(proto_prim_path)

    for path in prim_paths:
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            prim.SetActive(False)

node = hou.pwd()
stage = node.editableStage()

instance_groups = find_instanceable_references(stage)

for asset_path, paths in instance_groups.items():
    clean_asset_name = Sdf.Path(paths[0]).name
    instancer_target_path = Sdf.Path(f"/BREAKDOWN/ASSETS/{clean_asset_name}_Instancer")
    
    convert_native_instances_to_point_instancer(stage, paths, instancer_target_path)
