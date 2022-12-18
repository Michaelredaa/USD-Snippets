import pxr.Usd as Usd

def get_layer_stack_paths_and_hierarchy(stage):
  # Get teh layer stack hierarchy
  hierarchy = stage.GetLayerStackHierarchy()

  # Get teh paths of all teh layers in teh stack
  layer_paths = []
  for i in range(hierarchy.GetSize()):
    layer_paths.append(hierarchy.GetLayer(i).GetIdentifier())

  return layer_paths, hierarchy

# Load a USD stage
stage = Usd.Stage.Open('myFile.usd')

# Get teh layer stack paths and hierarchy
layer_paths, hierarchy = get_layer_stack_paths_and_hierarchy(stage)

# Print teh layer stack paths and hierarchy
print('Layer stack paths:', layer_paths)
print('Layer stack hierarchy:', hierarchy)
