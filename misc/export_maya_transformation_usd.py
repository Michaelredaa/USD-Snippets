import os
from pxr import UsdGeom, Usd
from contextlib import contextmanager

import maya.cmds as cmds

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


def create_bbox(node):
    x1, y1, z1, x2, y2, z2 = cmds.exactWorldBoundingBox(node, calculateExactly=True)

    cube = cmds.polyCube(n=node + '_bbox')[0]
    cmds.move(x1, '%s.f[5]' % cube, x=True)
    cmds.move(y1, '%s.f[3]' % cube, y=True)
    cmds.move(z1, '%s.f[2]' % cube, z=True)
    cmds.move(x2, '%s.f[4]' % cube, x=True)
    cmds.move(y2, '%s.f[1]' % cube, y=True)
    cmds.move(z2, '%s.f[0]' % cube, z=True)

    cmds.parent(cube, node)
    cmds.setAttr(cube + '.v', 0)

    return cube, x2 - x1, y2 - y1, z2 - z1


def import_usd_proxy(usd_file):
    """
    To import usd file and create stage in maya
    @param usd_file: the path of usd file
    @return: list(transformNode, shapeNode)
    """
    usd_shape = cmds.createNode('mayaUsdProxyShape')
    usd_transform = cmds.listRelatives(usd_shape, p=1)[0]
    usd_transform = cmds.rename(usd_transform, os.path.basename(usd_file).rsplit('.')[0])
    usd_shape = cmds.listRelatives(usd_transform, s=1)[0]
    cmds.setAttr(usd_shape + '.filePath', usd_file, type='string')
    cmds.setAttr(usd_shape + '.shareUsdStage', 0)
    cmds.setAttr(usd_shape + '.shareStage', 0)
    return usd_transform, usd_shape


def get_selected_hierarchy():
    """
    To get the hierarchy groups to the usd file as dict
    @return: dict of path-to-usd and the usd-file-path
    """
    usd_shapes_dict = {}

    def get_children(node):
        children = cmds.listRelatives(node, c=1, f=1)
        for child in children:
            shapes = cmds.listRelatives(child, c=1, f=1)
            if cmds.nodeType(shapes[0]) == 'mayaUsdProxyShape' and shapes:
                usd_shapes_dict[child] = cmds.getAttr(shapes[0] + '.filePath')
            else:
                get_children(child)

    for xform in cmds.ls(sl=1, l=1):
        get_children(xform)

    return usd_shapes_dict


def get_grps(usd_shapes_dict):
    """
    To get unique group that contains usd
    @param usd_shapes_dict: dict of path-to-usd and the usd-file-path
    @return: dict of groups with transformation
    """
    grps = []
    for usd_grp in usd_shapes_dict:
        grps.extend([usd_grp.rsplit('|', i)[0] for i in range(usd_grp.count('|'))])

    grps = list(set(grps))
    grps.sort()

    grps_transformation = {}
    for grp in grps:
        t = cmds.xform(grp, q=1, t=1)
        r = cmds.xform(grp, q=1, ro=1)
        s = cmds.xform(grp, q=1, s=1)

        rp = cmds.xform(grp, q=1, rp=1)
        sp = cmds.xform(grp, q=1, sp=1)
        p = cmds.xform(grp, q=1, piv=1)
        rpt = cmds.getAttr(grp + '.rotatePivotTranslate')[0]
        spt = cmds.getAttr(grp + '.scalePivotTranslate')[0]

        grps_transformation[grp] = {'t': t, 'r': r, 's': s, 'rp': rp, 'sp': sp, 'rpt': rpt, 'spt': spt, 'p': p}

    return grps_transformation


def create_usd(usd_file):
    """
    To get the maya groups hierarchy and recreate usd prims
    @param usd_file: the usd file path
    @return: None
    """
    usd_shapes = get_selected_hierarchy()
    grps_transformation = get_grps(usd_shapes)

    with open_stage(usd_file) as stage:
        for grp in grps_transformation:
            xformPrim = UsdGeom.Xform.Define(stage, grp.replace('|', '/'))
            prim = xformPrim.GetPrim()

            if grp.count('|') <= 1:
                prim.SetMetadata('kind', 'component')
            else:
                prim.SetMetadata('kind', 'subcomponent')

            t = grps_transformation[grp]['t']
            r = grps_transformation[grp]['r']
            s = grps_transformation[grp]['s']
            p = grps_transformation[grp]['p']
            rp = grps_transformation[grp]['rp']
            sp = grps_transformation[grp]['sp']
            rpt = grps_transformation[grp]['rpt']

            xformApi = UsdGeom.XformCommonAPI(xformPrim)

            if sum(t) != 0:
                xformApi.SetTranslate(t)

            if sum(r) != 0:
                xformApi.SetRotate(r)

            if sum(s) != 3:
                xformApi.SetScale(s)

            if sum(rp) != 0:
                xformApi.SetPivot(rp)

            # prim.CreateAttribute("xformOp:translate:rotatePivot", Sdf.ValueTypeNames.Vector3f)
            # prim.CreateAttribute("xformOp:translate:scalePivot", Sdf.ValueTypeNames.Vector3f)
            # prim.CreateAttribute("xformOp:translate:rotatePivotTranslate", Sdf.ValueTypeNames.Vector3f)

            # prim.GetAttribute("xformOp:translate:rotatePivot").Set(tuple(rp))
            # prim.GetAttribute("xformOp:translate:scalePivot").Set(tuple(sp))
            # prim.GetAttribute("xformOp:translate:rotatePivotTranslate").Set(tuple(rpt))

            if sum(t) == 0 and sum(r) == 0 and sum(s) == 3:
                prim.SetMetadata('kind', '')
                prim.SetMetadata('typeName', 'Scope')

            if grp in usd_shapes:
                prim.GetReferences().AddReference(usd_shapes[grp])

def main():
    create_usd("/comp.usda")


if __name__ == '__main__':
    main()
