"""Build ValueClip USDs and per-frame mesh snapshots from an animated USD.

Copies a filtered transform hierarchy from the input into an in-memory stage,
writes a static baseline layer, one layer per time sample for animted mesh attributes,
and a root USD that valueClips those files across the given frame range.
Run as a script (see main) or import process and the stage helpers.
"""

import argparse
import logging
import enum
import os

from pxr import Usd, UsdGeom, Sdf, Vt, Gf

# Configure logger
logger = logging.getLogger("usd_valueclip")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)


# Constants
MESH_ATTRS = ["extent", "points", "normals"]

class AttrCopyMode(enum.Enum):
    ALL = "all"
    STATIC = "static"
    FRAME = "frame"


def is_empty_prim(prim):
    """Check if a prim is empty.

    Args:
        prim (Usd.Prim): The prim to check.

    Returns:
        bool: True if the prim is empty, False otherwise.
    """
    if prim.IsA(UsdGeom.Xform) or prim.GetTypeName() == "Scope":
        if not list(prim.GetChildren()) and len(list(prim.GetAuthoredAttributes())) == 0:
            return True
    return False


def is_transformable_prim(prim):
    """Check if a prim is a transformable prim.

    Args:
        prim (Usd.Prim): The prim to check.

    Returns:
        bool: True if the prim is a transformable prim, False otherwise.
    """
    if prim.IsA(UsdGeom.Xformable):
        return True

    return any(child.IsA(UsdGeom.Xformable) for child in prim.GetDescendants())


def iter_stage_prims(stage):
    """Depth-first iteration over all prims under ``stage``, excluding the pseudo-root."""
    for prim in Usd.PrimRange(stage.GetPseudoRoot()):
        if prim != stage.GetPseudoRoot():
            yield prim


def delete_file_if_exists(filepath):
    """Delete the file if it already exists.

    Args:
        filepath (str): The path to the file to delete.
    """
    try:
        if os.path.exists(filepath):
            logger.info(f"Deleting existing file: {filepath}")
            os.remove(filepath)
    except Exception as e:
        logger.error(f"Error deleting file {filepath}: {e}")


def copy_prim_metadata(src_prim, dst_prim):
    """Copy all metadata from src_prim to dst_prim.

    Args:
        src_prim (Usd.Prim): Source prim.
        dst_prim (Usd.Prim): Destination prim.
    """
    for key, value in src_prim.GetAllMetadata().items():
        dst_prim.SetMetadata(key, value)


def copy_prim_attributes(src_prim, dst_prim, frame=None, attr_copy_mode=AttrCopyMode.STATIC, mask_attrs=None):
    """Copy attributes and metadata from src_prim to dst_prim.

    Args:
        src_prim (Usd.Prim): Source prim.
        dst_prim (Usd.Prim): Destination prim.
        frame (int, optional): Frame to export. If None, exports default values when no range is given.
        start_frame (int, optional): Start frame (inclusive).
        end_frame (int, optional): End frame (exclusive).
    """

    for src_attr in src_prim.GetAttributes():
        if mask_attrs and src_attr.GetName() not in mask_attrs:
            continue

        if not src_attr.HasValue():
            continue

        dst_attr = dst_prim.CreateAttribute(
            src_attr.GetName(),
            src_attr.GetTypeName(),
            custom=src_attr.IsCustom()
            )
        
        times = src_attr.GetTimeSamples()
        if times:
            if attr_copy_mode == AttrCopyMode.STATIC:
                value = src_attr.Get(time=times[0])
                if not value:
                    value = src_attr.Get()
                dst_attr.Set(value)
            elif attr_copy_mode == AttrCopyMode.FRAME:
                value = src_attr.Get(frame)
                if value:
                    dst_attr.Set(value, time=frame)

            elif attr_copy_mode == AttrCopyMode.ALL:
                for time in times:
                    value = src_attr.Get(time=time)
                    if value:
                        dst_attr.Set(value, time=time)
                    else:
                        dst_attr.Set(value)
        else:
            value = src_attr.Get()
            dst_attr.Set(value)

        for key, value in dst_attr.GetAllMetadata().items():
            dst_attr.SetMetadata(key, value)


def clean_stage(stage):
    """Copy prims into a new in-memory USD stage.

    Args:
        stage (Usd.Stage): The source USD stage.

    Returns:
        tuple: The root prim and the new in-memory stage.
    """
    clean_stage = Usd.Stage.CreateInMemory()

    root_prim = None
    for prim in iter_stage_prims(stage):
        if root_prim is None:
            root_prim = prim
        
        if is_empty_prim(prim):
            continue

        if not is_transformable_prim(prim):
            continue

        dst_prim = clean_stage.DefinePrim(prim.GetPath(), prim.GetTypeName())
        copy_prim_metadata(prim, dst_prim)
        copy_prim_attributes(prim, dst_prim, attr_copy_mode=AttrCopyMode.ALL)

    return root_prim, clean_stage


def export_usd_snapshot(in_stage, output_usd, frame=None, attr_copy_mode=AttrCopyMode.STATIC, mask_attrs=None):
    """Export a static snapshot of the USD stage at a specific frame.

    Args:
        in_stage (Usd.Stage): The input USD stage.
        output_usd (str): Output USD file path.
        frame (int, optional): Frame to export. If None, exports default values.
    """
    logger.info(f"Exporting {attr_copy_mode.value} to: {output_usd} ...")
    out_stage = Usd.Stage.CreateNew(output_usd)
    for prim in iter_stage_prims(in_stage):
        out_prim = out_stage.DefinePrim(prim.GetPath(), prim.GetTypeName())
        copy_prim_attributes(prim, out_prim, frame, attr_copy_mode, mask_attrs)
        copy_prim_metadata(prim, out_prim)
    out_stage.GetRootLayer().Save()


def build_valueclip(
    static_usd_path,
    frame_files,
    output_path,
    start_frame,
    end_frame,
    root_prim,
):
    """Create a USD ValueClip stage.

    Args:
        static_usd_path (str): Path to the static mesh USD file.
        frame_files (list): List of (remapped_frame, filepath) or filepaths.
        output_path (str): Output USD file path.
        start_frame (int): Original Maya start frame (clip timing offset).
        end_frame (int): End frame for the clip.
        root_prim (Usd.Prim): The root geometry prim.

    Returns:
        str: Output USD file path.
    """
    stage = Usd.Stage.CreateNew(output_path)
    stage.SetStartTimeCode(start_frame)
    if end_frame is None:
        end_frame = start_frame + len(frame_files) - 1
    stage.SetEndTimeCode(end_frame)
    rel_static = os.path.relpath(static_usd_path, os.path.dirname(output_path))
    stage.GetRootLayer().subLayerPaths.append(rel_static)
    asset_paths = []
    times = []
    active = []
    for i, f in enumerate(frame_files):
        if isinstance(f, (list, tuple)):
            frame, path = f
        else:
            frame, path = i, f
        rel = os.path.relpath(path, os.path.dirname(output_path))
        asset_paths.append(Sdf.AssetPath(rel))
        t = start_frame + i
        times.append(Gf.Vec2d(t, i))
        active.append(Gf.Vec2d(t, i))
    times = Vt.Vec2dArray(times)
    active = Vt.Vec2dArray(active)
    prim = stage.OverridePrim(root_prim.GetPath())
    clips_dict = {
        "default": {
            "assetPaths": asset_paths,
            "times": times,
            "primPath": str(root_prim.GetPath()),
            "active": active,
            "interpolateMissingClipValues": False,
        }
    }
    prim.SetMetadata("clips", clips_dict)
    logger.info(f"ValueClip USD written: {output_path}")
    stage.GetRootLayer().Save()
    return output_path


def process(source_anim_file, start_frame, end_frame, static_usd_file=None, anim_usd_file=None):
    """Process the USD file to create static snapshot and ValueClip.

    Args:
        source_anim_file (str): Input animated USD file path.
        start_frame (int): Start frame (inclusive).
        end_frame (int): End frame (exclusive).
        static_usd_file (str): Output static USD file path.
        anim_usd_file (str): Output ValueClip USD file path.
    """
    if not os.path.exists(source_anim_file):
        raise FileNotFoundError(f"Error: Animated USD file does not exist: {source_anim_file}")
    
    stage = Usd.Stage.Open(source_anim_file)
    root_prim, stage = clean_stage(stage)

    extention = os.path.splitext(source_anim_file)[1]
    
    if not static_usd_file:
        static_usd_file = source_anim_file.replace(f"{extention}", ".static.usd")
        delete_file_if_exists(static_usd_file)

    if not anim_usd_file:
        anim_usd_file = source_anim_file.replace(f"{extention}", ".anim.usd")
        delete_file_if_exists(anim_usd_file)

    export_usd_snapshot(stage, static_usd_file, attr_copy_mode=AttrCopyMode.STATIC)

    anim_frames_files = []
    for frame in range(start_frame, end_frame):
        frame_usd_file = source_anim_file.replace(f"{extention}", f".frame.{frame}.usd")
        delete_file_if_exists(frame_usd_file)
        export_usd_snapshot(stage, frame_usd_file, frame=frame, attr_copy_mode=AttrCopyMode.FRAME, mask_attrs=MESH_ATTRS)
        anim_frames_files.append(frame_usd_file)
    build_valueclip(static_usd_file, anim_frames_files, anim_usd_file, start_frame, end_frame, root_prim)


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description="USD ValueClip and Static Snapshot Utility")
    parser.add_argument("input_usd", help="Input animated USD file path")
    parser.add_argument("--start-frame", type=int, default=900, help="Start frame (inclusive)")
    parser.add_argument("--end-frame", type=int, default=905, help="End frame (exclusive)")
    parser.add_argument("--static-file-out", help="Output static USD file path (default: input with .static.usd)")
    parser.add_argument("--anim-file-out", help="Output anim USD file path (default: input with .anim.usd)")
    args = parser.parse_args()
    
    process(
        args.input_usd,
        args.start_frame,
        args.end_frame,
        static_usd_file=args.static_file_out,
        anim_usd_file=args.anim_file_out
    )

if __name__ == "__main__":
    main()

