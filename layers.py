# -*- coding: utf-8 -*-
"""
Documentation:
"""
from pxr import Sdf, Usd



stage_path = r'C:\Program Files\Side Effects Software\Houdini 19.5.303\houdini\usd\assets\squab\squab.usd'


stage = Usd.Stage.Open(stage_path)


def traversal_kernel(spec_path: Sdf.Path):
    spec = layer.GetObjectAtPath(spec_path)
    print(spec.__class__.__name__)
    if spec_path.IsPrimPath():
        print("prim", spec_path)

    if spec_path.IsPropertyPath():
        print("attr", spec_path)

    if spec_path.IsTargetPath():
        print("target", spec_path)

    if spec_path.IsPrimVariantSelectionPath():
        print('var', spec_path)



layer = Sdf.Layer.FindOrOpen(stage_path)
layer.Traverse(layer.pseudoRoot.path, traversal_kernel)




if __name__ == '__main__':
    print(__name__)
