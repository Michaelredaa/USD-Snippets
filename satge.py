import os

from contextlib import contextmanager
from pxr import Usd, Sdf


def resolve_path(stage: Usd.Stage, external_path: str):
    return stage.ResolveIdentifierToEditTarget(external_path)


@contextmanager
def open_stage(filepath):
    """Open or create stage"""
    filedir = os.path.dirname(filepath)

    if not os.path.isdir(filedir):
        os.makedirs(filedir)

    # stage = Usd.Stage.CreateInMemory("temp.usda")
    if os.path.isfile(filepath):
        stage = Usd.Stage.Open(filepath)
    else:
        stage = Usd.Stage.CreateNew(filepath)

    try:
        yield stage
    finally:
        stage.Save()


@contextmanager
def open_layer(filepath):
    """Open or create layer"""
    filedir = os.path.dirname(filepath)

    if not os.path.isdir(filedir):
        os.makedirs(filedir)

    if os.path.isfile(filepath):
        layer = Sdf.Layer.FindOrOpen(filepath)
    else:
        layer = Sdf.Layer.CreateNew(filepath)

    try:
        yield layer
    finally:
        layer.Save()


def create_stage_with_sublayer(stage_filepath, sublayer_paths):
    """
    To open or create stage and add sublayer inside
    @param stage_filepath: (str) the path of main stage
    @param sublayer_paths: (list(str)) the paths of sublayer
    @return:
    """
    with open_stage(stage_filepath) as stage:
        root_layer = stage.GetRootLayer()
        for sublayer_path in sublayer_paths:
            with open_layer(sublayer_path) as sublayer:
                if sublayer.identifier not in root_layer.subLayerPaths:
                    root_layer.subLayerPaths.append(sublayer.identifier)
