from pxr import Usd, Sdf, UsdUtils

def generate_valueclip(stage_prim, times, clip_usd_file, clip_prim_path_str=None, clip_name="default", use_file_duration=True):
    """
    Sets up a ValueClip on the given USD stage with the specified animation and clip data.

    :param stage_prim: Usd.Prim
        The USD stage prim to apply the clip to.
    :param clip_prim_path_str: str
        The path to the USD clip prim containing animation data.
    :param times: list of tuples [(clip_start, clip_end), (anim_start, anim_end)]
        Start and end times for the clip and animation.
    :param clip_usd_file: str
        Path to the USD file containing the clip data.
    :param clip_name: str, optional
        Name for the clip set (default is "default").

    :return: None
        Modifies the USD prims without returning a value.
    """
    stage = Usd.Stage.Open(clip_usd_file)
    
    if use_file_duration:
        for prim in stage.Traverse():
            if prim.GetTypeName() == 'Mesh':
                time_sample = prim.GetAttribute("points").GetTimeSamples()
                clip_start = time_sample[0]
                clip_end = time_sample[-1]
                break
        (anim_start, anim_end) = times
    else:
        (clip_start, clip_end), (anim_start, anim_end) = times
        
    clip_duration = clip_end - clip_start

    active_times = [(t, clip_start) for t in range(anim_start, anim_end + 1, clip_duration)]
    clip_times = [
        (t, clip_start) if i % 2 == 0 else (t, clip_duration)
        for i, t in enumerate(range(anim_start, anim_end + 1, clip_duration))
    ]

    if not clip_prim_path_str:
        for prim in stage.Traverse():
            clip_prim_path_str =  prim.GetPath().pathString
            break

    clipsAPI = Usd.ClipsAPI(stage_prim)
    clipsAPI.SetClipActive(active_times, clip_name)
    clipsAPI.SetClipTimes(clip_times, clip_name)
    clipsAPI.SetClipAssetPaths([Sdf.AssetPath(clip_usd_file)], clip_name)
    clipsAPI.SetClipPrimPath(clip_prim_path_str, clip_name)
