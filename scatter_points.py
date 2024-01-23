import random
import numpy as np

from pxr import Usd, Sdf, UsdGeom

node = hou.pwd()
stage = node.editableStage()

prim = stage.GetPrimAtPath("/grid1/mesh_0")

# random data
scatter = hou.ch("scatter_points")


def random_groups_vectors(num_values: int, num_groups: int, seed=101) -> np.ndarray:
    """
    Generate random vectors and distribute them into groups.
    """
    np.random.seed(seed)
    random_pairs = np.random.rand(num_values, 2)
    np.random.shuffle(random_pairs)

    group_indices = np.random.randint(0, num_groups, num_values)

    groups = [random_pairs[group_indices == i] for i in range(num_groups)]

    return np.array(groups)


def scatter_points(prim, num_points, seed=101):
    mesh = UsdGeom.Mesh(prim)

    points_attr = mesh.GetPointsAttr()
    fvCount_attr = mesh.GetFaceVertexCountsAttr()
    fvIndices_attr = mesh.GetFaceVertexIndicesAttr()

    points_values = np.array(points_attr.Get())
    fvIndices_values = np.array(fvIndices_attr.Get())

    faces_values = fvIndices_values.reshape(-1, 4)

    random_values_list = random_groups_vectors(num_points, faces_values.shape[0], seed=seed)

    new_points = []
    for i, face in enumerate(faces_values):

        p0 = points_values[face[0]]
        p1 = points_values[face[1]]
        p2 = points_values[face[2]]
        p3 = points_values[face[3]]

        v1 = p1 - p0
        v2 = p3 - p0

        for r1, r2 in random_values_list[i]:
            # barycentric coordinates
            newp = p0 + (r1 * v1) + (r2 * v2)
            new_points.append(newp)

    return np.array(new_points)


particle_set = UsdGeom.Points.Define(stage, '/grid1/points')
particle_set.CreatePointsAttr(scatter_points(prim, scatter))















