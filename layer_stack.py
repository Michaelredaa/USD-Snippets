from pxr import Usd

usd_file = r"/path/to/usd/asset.usda"

stage = Usd.Stage.Open(usd_file)

layer_stack = stage.GetLayerStack()

for lyr in layer_stack:
    print(lyr)

root_layer = stage.GetRootLayer()
# refs = root_layer.GetExternalReferences()
refs = root_layer.GetLoadedLayers()
layer_paths = [str(x.resolvedPath).replace('\\', '/') for x in refs if str(x.resolvedPath)]
print(layer_paths)


