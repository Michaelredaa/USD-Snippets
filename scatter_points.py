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

def scatter_points_with_dis(prim, num_points, min_distance= 0.1, seed=101):

    mesh = UsdGeom.Mesh(prim)

    points_attr = mesh.GetPointsAttr()
    fvCount_attr = mesh.GetFaceVertexCountsAttr()
    fvIndices_attr = mesh.GetFaceVertexIndicesAttr()

    points_values = np.array(points_attr.Get())
    fvIndices_values = np.array(fvIndices_attr.Get())

    faces_values = fvIndices_values.reshape(-1, 4)

    random_values_list = random_groups_vectors(num_points, faces_values.shape[0], seed=seed)

    new_points = np.empty((0, 3), dtype=np.float32)
    for i, face in enumerate(faces_values):

        p0 = points_values[face[0]]
        p1 = points_values[face[1]]
        p2 = points_values[face[2]]
        p3 = points_values[face[3]]

        v1 = p1 - p0
        v2 = p3 - p0

        
        # newp = p0 + (r1 * v1) + (r2 * v2)
        
        # for r1, r2 in random_values_list[i]:
        #     # barycentric coordinates
        #     newp = p0 + (r1 * v1) + (r2 * v2)
            
        #     if all(np.linalg.norm(newp-existing_point) >= min_distance for existing_point in new_points):
        #         new_points.append(newp)
        
        
        candidate_points = p0 + (random_values_list[i][:, 0, np.newaxis] * v1) + (random_values_list[i][:, 1, np.newaxis] * v2)
        # Check the distance to existing points
        distances = np.linalg.norm(candidate_points[:, np.newaxis] - new_points, axis=2)
        if np.all(distances >= min_distance):
            new_points = np.vstack((new_points, candidate_points))

particle_set = UsdGeom.Points.Define(stage, '/grid1/points')
particle_set.CreatePointsAttr(scatter_points(prim, scatter))















