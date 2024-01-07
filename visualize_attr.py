# -*- coding: utf-8 -*-
"""
Documentation:
"""
from pxr import Usd, UsdGeom, Vt
import numpy as np


def normalize_2d_array(arr: np.array):
    col_ranges = np.max(arr, axis=0) - np.min(arr, axis=0)
    normalized_arr = (arr - np.min(arr, axis=0)) / col_ranges
    return normalized_arr


def interpolate_colors(normalized_data, color_positions, colors):
    colored_data = np.zeros_like(normalized_data)

    for i in range(3):  # Iterate over RGB channels
        colored_data[:, i] = np.interp(normalized_data[:, i], color_positions, colors[:, i])

    return colored_data


def visualize_attr(prim: Usd.Prim, attr_name: str, time=0, channel=None, normalize=False,
                   multiplier=1.0, ramp_colors=[[(0, 0, 0), (1, 1, 1)], [0, 1]]):
    attr = prim.GetAttribute(attr_name)

    if not attr.HasValue():
        return

    attr_values = np.array(attr.Get(time))
    if normalize:
        attr_values = normalize_2d_array(attr_values)
    attr_values = attr_values * multiplier
    attr_shape = attr_values.shape

    if channel is not None and len(attr_shape) not in [0, 1]:
        if channel < attr_shape[1]:
            attr_values = attr_values[:, channel]

    attr_shape = attr_values.shape
    if len(attr_shape) in [0, 1]:
        attr_values = np.repeat(attr_values.reshape(-1, 1), 3, axis=1)
    elif len(attr_shape) > 1 and attr_shape[1] == 2:
        attr_values = np.hstack((attr_values, np.zeros((attr_shape[0], 1))))

    displayColor_attr = UsdGeom.Mesh(prim).GetDisplayColorAttr()
    interpolation = attr.GetMetadata("interpolation")
    if not interpolation:
        interpolation = 'vertex'

    displayColor_attr.SetMetadata('interpolation', interpolation)

    if normalize:
        colors, color_points = ramp_colors
        color_points = np.array(color_points)
        colors = np.array(colors)
        attr_values = interpolate_colors(attr_values, color_points, colors)

    displayColor_attr.Set(Vt.Vec3fArray.FromNumpy(attr_values), time)


if __name__ == '__main__':
    print(__name__)
