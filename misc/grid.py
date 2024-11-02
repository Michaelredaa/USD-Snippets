# -*- coding: utf-8 -*-
"""
Documentation: This script used inside python node to create a usd geom as a grid
"""

import math
from pxr import Usd, UsdGeom, Sdf, Vt


def create_uv(mesh: UsdGeom.Mesh):
    points_attr = mesh.GetPointsAttr()
    face_vertex_indices = mesh.GetFaceVertexIndicesAttr().Get()

    points = points_attr.Get()

    min_x = min(points, key=lambda l: l[0])[0]
    max_x = max(points, key=lambda l: l[0])[0]
    size_x = max_x - min_x

    min_z = min(points, key=lambda l: l[2])[2]
    max_z = max(points, key=lambda l: l[2])[2]
    size_z = max_z - min_z

    st_values = []
    for i in range(0, len(face_vertex_indices), 4):
        indices = face_vertex_indices[i:i + 4]
        for idx in indices:
            st_value = [
                (points[idx][0] - min_x) / size_x,
                1 - (points[idx][2] - min_z) / size_z
            ]
            st_values.append(st_value)

    # Create the "uv" attribute

    st_attr = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                      interpolation=UsdGeom.Tokens.faceVarying)
    st_attr.Set(Vt.Vec2fArray(st_values))


def rotate_point(point: list, angle: list) -> tuple:
    x, y, z = point
    qx, qy, qz = point

    # @X
    if angle[0] != 0:
        rad = math.radians(angle[0])
        qz = z * math.cos(rad) - y * math.sin(rad)
        qy = z * math.sin(rad) + y * math.cos(rad)
        x, y = qx, qy

    # @Y
    if angle[1] != 0:
        rad = math.radians(angle[1])
        qx = x * math.cos(rad) + z * math.sin(rad)
        qz = -x * math.sin(rad) + z * math.cos(rad)
        x, y = qx, qy

    # @Z
    if angle[2] != 0:
        rad = math.radians(angle[2])
        qx = x * math.cos(rad) - y * math.sin(rad)
        qy = x * math.sin(rad) + y * math.cos(rad)

    return qx, qy, qz


def create_grid(
        stage: Usd.Stage,
        prim_path: str,
        rows: int,
        columns: int,
        size: list[float],
        orientation: str,
        center: list[float],
        rotate: list[float],

) -> UsdGeom.Mesh:
    # Add Mesh
    mesh = UsdGeom.Mesh.Define(stage, prim_path)

    # Add points
    points = []

    for r in range(rows):
        for c in range(columns):
            x = (r / (rows - 1) - 0.5) * size[0]
            y = 0
            z = (c / (columns - 1) - 0.5) * size[1]

            point = (x, y, z)

            if orientation == 'xy':
                point = (y, x, z)

            if orientation == 'yz':
                point = (y, x, z)

            point = rotate_point(point, rotate)

            point = [(point[i] + center[i]) + point[i] for i in range(3)]

            points.append(point)

        # Face Vertrics Count
    vertic_count = [4] * (rows - 1) * (columns - 1)
    mesh.CreateFaceVertexCountsAttr(vertic_count)

    # Create Faces

    vertex_indices = []
    for r in range(rows - 1):
        for c in range(columns - 1):
            idx = r * columns + c
            face = [idx, idx + 1, idx + 1 + columns, idx + columns]
            vertex_indices.extend(face)

    mesh.CreateFaceVertexIndicesAttr(vertex_indices)

    mesh.CreatePointsAttr(points)

    create_uv(mesh)

    return mesh


if __name__ == '__main__':
    # create_grid(prim_path, rows, columns, size, orientation, center, rotate)

    stage = Usd.Stage.CreateInMemory()
    create_grid(stage, "/grid", 50, 50, (10, 10), '', (0, 0, 0), (0, 0, 0))
    stage.GetRootLayer().Export("grid.usd")
