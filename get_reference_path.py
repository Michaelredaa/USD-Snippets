

def get_reference_path(prim):
    return prim.GetMetadata('references').GetAddedOrExplicitItems()[0].assetPath


def get_payload_path(prim):
    return prim.GetMetadata('payload').GetAddedOrExplicitItems()[0].assetPath
