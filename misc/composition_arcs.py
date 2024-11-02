from pxr import Usd, Sdf


def get_references_paths(prim: Usd.Prim):
    ref_specs = prim.GetMetadata('references').GetAddedOrExplicitItems()
    return [ref_spec.assetPath for ref_spec in ref_specs]


def get_payload_path(prim: Usd.Prim):
    payload_specs = prim.GetMetadata('payload').GetAddedOrExplicitItems()[0].assetPath
    return [payload_spec.assetPath for payload_spec in payload_specs]
