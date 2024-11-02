from pathlib import Path

import mayaUsd as mu

from pxr import Usd

def get_layer_by_name(stage, layer_name):

    for layer in stage.GetLayerStack():
        layer_path = Path(layer.realPath)
        if layer_name in layer_path.stem:
            return layer
          
def get_stage_from_maya_node(node):
  shapes = cmds.ls(node, type='mayaUsdProxyShape', long=True)
  if not shapes:
    raise RuntimeError(f'`{node}` if not a `mayaUsdProxyShape` node')

  stage = mu.ufe.getStage(shapes[0])
  return stage

def get_selected_prim():
  
  for sel in cmds.ls(sl=1, ufe=1):
      if '/' not in sel:
          continue
      prim = mu.ufe.ufePathToPrim(sel)

def get_current_stage():
    prim = get_selected_prim()
    stage = prim.GetStage()
    return stage


import mayaUsd as mu
from pxr import UsdGeom

shape = cmds.ls(sl=1)

def get_bound_geoms():
    for sel in cmds.ls(sl=1, ufe=1):
        if ',' not in sel:
            continue
        
        proxy_shape = sel.split(',')[0]
        selected_prim = mu.ufe.ufePathToPrim(sel)
        
        prim_type = selected_prim.GetTypeName()
        
        if prim_type != 'Material':
            continue
        
        material_path = selected_prim.GetPath()
        
        stage = selected_prim.GetStage()
        
        
        geom_prims = []
        
        for prim in stage.Traverse():
            if not prim.IsA(UsdGeom.Imageable):
                continue
                
            material_rel = prim.GetRelationship('material:binding')
            
            if not material_rel.IsValid():
                continue
            
            if material_path in material_rel.GetTargets():
                geom_prims.append(prim)
                
        return proxy_shape, geom_prims



def select_prims(proxy, prims):
    
    maya_prim_paths = [proxy+','+prim.GetPath().pathString for prim in prims]
    
    cmds.select(maya_prim_paths, r=1)
    
     
        
proxy, prims = get_bound_geoms()
select_prims(proxy, prims)




# stage.GetLayerStack()
# layer = stage.GetRootLayer()
# layer_path = layer.identifier

# stage = Usd.Stage.Open(layer.realPath)
