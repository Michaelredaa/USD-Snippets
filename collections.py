from pxr import Usd
def get_all_collections(prim: Usd.Prim) -> dict:
    data = {}
    for col in Usd.CollectionAPI.GetAllCollections(prim):
        data[col.GetName()] = [str(p.GetPrimPath()) for p in col.GetIncludesRel().GetTargets()]

    return data


def get_collection_by_name(prim: Usd.Prim, col_name: str) -> Usd.CollectionAPI:
    collection_prim = Usd.CollectionAPI.GetCollection(prim, col_name)
    return collection_prim
