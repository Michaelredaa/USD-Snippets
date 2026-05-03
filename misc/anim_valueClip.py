import argparse
import logging
import enum
import os
from typing import Optional, Tuple, List, Union

from pxr import Usd, UsdGeom, Sdf, Vt, Gf


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("usd_valueclip")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    return logger


logger = setup_logger()

MESH_ATTRS: List[str] = ["extent", "points", "normals", "xformOp:transform"]
ROOT_PRIM = "/root"

class AttrCopyMode(enum.Enum):
    """Attribute copy modes for USD export."""
    ALL = "all"
    STATIC = "static"
    FRAME = "frame"


def is_empty_prim(prim: Usd.Prim) -> bool:
    """Check whether a prim is empty (no children or attributes)."""
    if prim.IsA(UsdGeom.Xform) or prim.GetTypeName() == "Scope":
        if not list(prim.GetChildren()) and len(list(prim.GetAuthoredAttributes())) == 0:
            return True
    return False


def is_transformable_prim(prim: Usd.Prim) -> bool:
    """Check whether prim or descendants are transformable."""
    if prim.IsA(UsdGeom.Xformable):
        return True
    return any(child.IsA(UsdGeom.Xformable) for child in prim.GetChildren())


def iter_stage_prims(stage: Usd.Stage):
    """Yield all prims in stage excluding pseudo-root."""
    for prim in Usd.PrimRange(stage.GetPseudoRoot()):
        if prim != stage.GetPseudoRoot():
            yield prim


def delete_file_if_exists(filepath: str) -> None:
    """Delete file if it exists on disk."""
    try:
        if os.path.exists(filepath):
            logger.debug(f"Deleting file: {filepath}")
            os.remove(filepath)
    except Exception as e:
        logger.error(f"Error deleting file {filepath}: {e}")


def copy_prim_metadata(src_prim: Usd.Prim, dst_prim: Usd.Prim) -> None:
    """Copy all metadata from source prim to destination."""
    for key, value in src_prim.GetAllMetadata().items():
        dst_prim.SetMetadata(key, value)


def write_attr_values(
    src_attr: Usd.Attribute,
    dst_attr: Usd.Attribute,
    frame: Optional[int],
    mode: AttrCopyMode,
) -> None:
    """Write attribute values based on copy mode."""
    times = src_attr.GetTimeSamples()

    if times:
        if mode == AttrCopyMode.STATIC:
            value = src_attr.Get(time=times[0]) or src_attr.Get()
            dst_attr.Set(value)

        elif mode == AttrCopyMode.FRAME:
            value = src_attr.Get(frame)
            if value:
                dst_attr.Set(value, time=frame)

        elif mode == AttrCopyMode.ALL:
            for time in times:
                value = src_attr.Get(time=time)
                if value:
                    dst_attr.Set(value, time=time)
    else:
        dst_attr.Set(src_attr.Get())


def copy_prim_attributes(
    src_prim: Usd.Prim,
    dst_prim: Usd.Prim,
    frame: Optional[int] = None,
    attr_copy_mode: AttrCopyMode = AttrCopyMode.STATIC,
    mask_attrs: Optional[List[str]] = None,
) -> None:
    """Copy attributes from source to destination prim."""
    for src_attr in src_prim.GetAttributes():

        if mask_attrs and src_attr.GetName() not in mask_attrs:
            continue
        if not src_attr.HasValue():
            continue

        logger.debug(f"Copying attr: {src_attr.GetName()}")

        dst_attr = dst_prim.CreateAttribute(
            src_attr.GetName(),
            src_attr.GetTypeName(),
            custom=src_attr.IsCustom(),
        )

        write_attr_values(src_attr, dst_attr, frame, attr_copy_mode)

        for key, value in dst_attr.GetAllMetadata().items():
            dst_attr.SetMetadata(key, value)


def create_clean_stage(stage: Usd.Stage) -> Usd.Stage:
    """Create cleaned in-memory stage containing only valid prims."""
    clean_stage = Usd.Stage.CreateInMemory()

    for prim in iter_stage_prims(stage):
        if is_empty_prim(prim):
            logger.debug(f"Skipping empty prim: {prim.GetPath()}")
            continue

        if not is_transformable_prim(prim):
            logger.debug(f"Skipping non-transformable prim: {prim.GetPath()}")
            continue

        logger.debug(f"Adding prim: {prim.GetPath()}")
        
        prim_path = Sdf.Path(ROOT_PRIM + prim.GetPath().pathString)
        dst_prim = clean_stage.DefinePrim(
            prim_path,
             prim.GetTypeName()
            )
        copy_prim_metadata(prim, dst_prim)
        copy_prim_attributes(prim, dst_prim, attr_copy_mode=AttrCopyMode.ALL)

    clean_stage.SetDefaultPrim(
        clean_stage.GetPrimAtPath(ROOT_PRIM)
        )

    return clean_stage


def export_usd_snapshot(
    in_stage: Usd.Stage,
    output_usd: str,
    frame: Optional[int] = None,
    attr_copy_mode: AttrCopyMode = AttrCopyMode.STATIC,
    mask_attrs: Optional[List[str]] = None,
) -> None:
    """Export USD snapshot at given frame."""
    logger.info(f"Exporting {attr_copy_mode.value} {frame} -> {output_usd}")
    out_stage = Usd.Stage.CreateNew(output_usd)

    for prim in iter_stage_prims(in_stage):
        logger.debug(f"Exporting prim: {prim.GetPath()}")
        out_prim = out_stage.DefinePrim(prim.GetPath(), prim.GetTypeName())
        copy_prim_attributes(prim, out_prim, frame, attr_copy_mode, mask_attrs)
        copy_prim_metadata(prim, out_prim)

    out_stage.GetRootLayer().Save()


def build_frame_assets(
    frame_files: List[Union[str, Tuple[int, str]]],
    start_frame: int,
) -> Tuple[List[Sdf.AssetPath], Vt.Vec2dArray, Vt.Vec2dArray]:
    """Build asset/time mappings for value clip."""
    asset_paths: List[Sdf.AssetPath] = []
    times: List[Gf.Vec2d] = []
    active: List[Gf.Vec2d] = []

    for i, f in enumerate(frame_files):
        frame, path = f if isinstance(f, (list, tuple)) else (i, f)

        rel = os.path.relpath(path, os.path.dirname(frame_files[0]))
        asset_paths.append(Sdf.AssetPath(rel))

        t = start_frame + i
        times.append(Gf.Vec2d(t, i))
        active.append(Gf.Vec2d(t, i))

        logger.debug(f"Frame {frame} -> {path}")

    return asset_paths, Vt.Vec2dArray(times), Vt.Vec2dArray(active)


def build_valueclip(
    static_usd_path: str,
    frame_files: List[str],
    output_path: str,
    start_frame: int,
    end_frame: Optional[int],
    root_prim: Usd.Prim,
) -> str:
    """Build USD value clip from frame USDs."""
    stage = Usd.Stage.CreateNew(output_path)
    stage.SetStartTimeCode(start_frame)

    if end_frame is None:
        end_frame = start_frame + len(frame_files) - 1

    stage.SetEndTimeCode(end_frame)

    rel_static = os.path.relpath(static_usd_path, os.path.dirname(output_path))
    stage.GetRootLayer().subLayerPaths.append(rel_static)

    asset_paths, times, active = build_frame_assets(frame_files, start_frame)

    prim = stage.OverridePrim(root_prim.GetPath())

    prim.SetMetadata(
        "clips",
        {
            "default": {
                "assetPaths": asset_paths,
                "times": times,
                "primPath": str(root_prim.GetPath()),
                "active": active,
                "interpolateMissingClipValues": False,
            }
        },
    )

    logger.info(f"ValueClip written -> {output_path}")
    stage.GetRootLayer().Save()
    return output_path


def process(
    source_anim_file: str,
    start_frame: int,
    end_frame: int,
    static_usd_file: Optional[str] = None,
    anim_usd_file: Optional[str] = None,
) -> None:
    """Main USD processing pipeline."""
    if not os.path.exists(source_anim_file):
        raise FileNotFoundError(source_anim_file)

    logger.info(f"Processing: {source_anim_file}")

    stage = Usd.Stage.Open(source_anim_file)
    stage = create_clean_stage(stage)
    root_prim = stage.GetDefaultPrim()

    ext = os.path.splitext(source_anim_file)[1]

    if not static_usd_file:
        static_usd_file = source_anim_file.replace(ext, ".static.usd")
        delete_file_if_exists(static_usd_file)

    if not anim_usd_file:
        anim_usd_file = source_anim_file.replace(ext, ".anim.usd")
        delete_file_if_exists(anim_usd_file)

    export_usd_snapshot(stage, static_usd_file, attr_copy_mode=AttrCopyMode.STATIC)

    anim_frames_files: List[str] = []

    for frame in range(start_frame, end_frame):
        frame_file = source_anim_file.replace(ext, f".frame.{frame}.usd")
        delete_file_if_exists(frame_file)

        logger.debug(f"Exporting frame {frame}")

        export_usd_snapshot(
            stage,
            frame_file,
            frame=frame,
            attr_copy_mode=AttrCopyMode.FRAME,
            mask_attrs=MESH_ATTRS,
        )

        anim_frames_files.append(frame_file)

    build_valueclip(static_usd_file, anim_frames_files, anim_usd_file, start_frame, end_frame, root_prim)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="USD ValueClip Utility")
    parser.add_argument("input_usd")
    parser.add_argument("--start-frame", type=int, default=900)
    parser.add_argument("--end-frame", type=int, default=905)
    parser.add_argument("--static-file-out")
    parser.add_argument("--anim-file-out")
    args = parser.parse_args()

    process(
        args.input_usd,
        args.start_frame,
        args.end_frame,
        static_usd_file=args.static_file_out,
        anim_usd_file=args.anim_file_out,
    )


if __name__ == "__main__":
    main()