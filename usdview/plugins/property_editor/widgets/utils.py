# -*- coding: utf-8 -*-
"""
Documentation:
"""

import functools
import traceback
import math

from collections.abc import Iterable

from PySide6 import QtCore, QtGui, QtWidgets
from pxr import Sdf, Gf, Usd

WidgetRoleData = QtCore.Qt.UserRole + 10
valueRoleData = QtCore.Qt.UserRole + 20

KeyFrameColor = "#468C46"
timeSamplesColor = "#40806D"


def is_scalar(variable):
    return isinstance(variable, (int, float, bool, complex, str, bytes, Sdf.AssetPath, Sdf.Path, type(None)))


def is_iterable(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (str, int, float))


def decompose_matrix(matrix):
    transform = Gf.Transform(matrix)
    translation = transform.GetTranslation()

    rotation_quat = transform.GetRotation().GetQuaternion()
    quatd = Gf.Quatd(rotation_quat.GetReal(), rotation_quat.GetImaginary())  # Create Gf.Quatd from real and imaginary parts

    rotation = Gf.Rotation()
    rotation.SetQuat(quatd)

    # Decompose rotation into Euler angles (YXZ order to avoid gimbal lock on Y rotations)
    euler_rotation = rotation.Decompose(Gf.Vec3d(1, 0, 0), Gf.Vec3d(0, 1, 0), Gf.Vec3d(0, 0, 1))
    scale = transform.GetScale()

    return translation, euler_rotation, scale


def compose_matrix(translation, rotation, scale):
    transform = Gf.Transform()

    transform.SetScale(Gf.Vec3d(*scale))

    # Apply rotation using Euler angles in YXZ order
    rotX = Gf.Rotation(Gf.Vec3d(1, 0, 0), rotation[0])
    rotY = Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation[1])
    rotZ = Gf.Rotation(Gf.Vec3d(0, 0, 1), rotation[2])
    combined_rotation = rotX * rotY * rotZ
    transform.SetRotation(combined_rotation)

    transform.SetTranslation(Gf.Vec3d(*translation))

    return transform.GetMatrix()


if __name__ == '__main__':
    print(__name__)
