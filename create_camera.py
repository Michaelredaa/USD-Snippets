from pxr import Usd, UsdGeom

node = hou.pwd()
stage = node.editableStage()

# Add code to modify the stage.
# Use drop down menu to select examples.
img_path = "/textureCards/{}camera.png"
prim = stage.GetPrimAtPath("/rubbertoy")

def set_cards(prim, xpos, ypos, zpos, nxpos=None, nypos=None, nzpos=None, enable=True):
    modelAPI = UsdGeom.ModelAPI(prim)
    
    if not modelAPI:
        return "Please select Model prim"
    
    modelAPI.CreateModelCardTextureXPosAttr(xpos)
    modelAPI.CreateModelCardTextureYPosAttr(ypos)
    modelAPI.CreateModelCardTextureZPosAttr(zpos)
    
    if nxpos:
        modelAPI.CreateModelCardTextureXNegAttr(xpos)
        
    if nypos:
        modelAPI.CreateModelCardTextureYNegAttr(xpos)
        
    if nzpos:
        modelAPI.CreateModelCardTextureZNegAttr(xpos)
        
    if enable:
        modelAPI.CreateModelDrawModeAttr(UsdGeom.Tokens.cards)
        modelAPI.CreateModelApplyDrawModeAttr(True)

        
def bbox_size(prim): # pxr.Gf.Vec3d
    imageable = UsdGeom.Imageable(prim)
    bound = imageable.ComputeWorldBound(Usd.TimeCode.Default(), UsdGeom.Tokens.default_)
    box_range = bound.ComputeAlignedBox()
        
    return box_range.GetSize()
        
        
cam = UsdGeom.Camera.Define(stage, "/cameras/cam")
# cam.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
# cam.CreateHorizontalApertureAttr(10)
# cam.CreateVerticalApertureAttr(10)
        
        
        
set_cards(prim, img_path.format('X'), img_path.format('Y'), img_path.format('Z'))
