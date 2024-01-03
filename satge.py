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


def copy_prim(source_stage: Usd.Stage, source_path: Sdf.Path,
              dist_stage: Usd.Stage, dist_path: Sdf.Path):
    sprim = source_stage.GetPrimAtPath(source_path)
    dprim = dist_stage.DefinePrim(dist_path, sprim.GetTypeName())
    Usd.ModelAPI(dprim).SetKind(Usd.ModelAPI(sprim).GetKind())

    for sprop in sprim.GetProperties():
        if isinstance(sprop, Usd.Relationship):
            targets = sprop.GetTargets()
            if targets:
                dprop = dprim.CreateRelationship(sprop.GetName())
                dprop.SetTargets(targets)

        elif isinstance(sprop, Usd.Attribute):
            value = sprop.Get()
            if value is not None:
                dattr = dprim.CreateAttribute(sprop.GetName(), sprop.GetTypeName())
                dattr.Set(value)
