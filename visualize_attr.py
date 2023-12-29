# -*- coding: utf-8 -*-
"""
Documentation:
"""
from pxr import Usd, UsdGeom, Vt
import numpy as np


def visualize_attr(prim: Usd.Prim, attr_name: str, time=0):
    attr = prim.GetAttribute(attr_name)

    if not attr.HasValue():
        return

    attr_values = np.array(attr.Get(time))

    attr_shape = attr_values.shape

    if len(attr_shape) in [0, 1]:
        attr_values = np.repeat(attr_values.reshape(-1, 1), 3, axis=1)
    elif len(attr_shape) > 1 and attr_shape[1] == 2:
        attr_values = np.hstack((attr_values, np.zeros((attr_shape[0], 1))))

    displayColor_attr = UsdGeom.Mesh(prim).GetDisplayColorAttr()
    displayColor_attr.SetMetadata('interpolation', attr.GetMetadata("interpolation"))

    displayColor_attr.Set(Vt.Vec3fArray.FromNumpy(attr_values), time)


if __name__ == '__main__':
    print(__name__)
