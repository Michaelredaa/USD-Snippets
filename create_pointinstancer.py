from pxr import Usd, Sdf, UsdGeom, Gf

def create_point_instancer(stage, instancer_path, indices, positions=None, orientations=None, scales=None):
    if scales is None:
        scales = []
    if orientations is None:
        orientations = []
    if positions is None:
        positions = []

    instancer_prim = UsdGeom.PointInstancer.Define(stage, instancer_path)
    prototypes_prim = UsdGeom.Scope.Define(stage, instancer_prim.GetPath().AppendChild('prototypes'))

    instancer_prim.GetProtoIndicesAttr()
    instancer_prim.CreatePrototypesRel().SetTargets([prototypes_prim.GetPath()])


    positions_array = []
    orientations_array = []
    scales_array = []

    for p in positions:
        positions_array.append(Gf.Vec3f(p[0], p[1], p[2]))

    for p in scales:
        scales_array.append(Gf.Vec3f(p[0], p[1], p[2]))

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
    
    
if __name__ == '__main__':
  create_point_instancer(stage, '/instancer', indices=[0, 0], positions=[[1, 0, 0], [0, 1, 1]], orientations=[[0, 30, 0], [0, 60, 10]])
