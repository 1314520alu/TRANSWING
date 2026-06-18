import csv
import math
from pathlib import Path

import FreeCAD as App
import Import
import Part


WORKDIR = Path(__file__).resolve().parent
STEP_FILES = list(WORKDIR.glob("*.step_tmp")) + list(WORKDIR.glob("*.step")) + list(WORKDIR.glob("*.stp"))
if not STEP_FILES:
    raise SystemExit("No STEP file found in workspace")

STEP_PATH = STEP_FILES[0]
OUT_OBJECTS = WORKDIR / "freecad_step_objects.csv"
OUT_CYLINDERS = WORKDIR / "freecad_step_cylinders.csv"
OUT_CIRCLES = WORKDIR / "freecad_step_circles.csv"


def vec_tuple(v):
    return (float(v.x), float(v.y), float(v.z))


def norm(v):
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def unit_tuple(v):
    n = norm(v)
    if n == 0:
        return (0.0, 0.0, 0.0)
    return (float(v.x / n), float(v.y / n), float(v.z / n))


def bbox_tuple(bb):
    return (
        float(bb.XMin),
        float(bb.YMin),
        float(bb.ZMin),
        float(bb.XMax),
        float(bb.YMax),
        float(bb.ZMax),
        float(bb.XLength),
        float(bb.YLength),
        float(bb.ZLength),
    )


def write_csv(path, rows, headers):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


doc = App.newDocument("step_extract")
Import.insert(str(STEP_PATH), doc.Name)
doc.recompute()

object_rows = []
cylinder_rows = []
circle_rows = []

for obj in doc.Objects:
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        continue

    bb = shape.BoundBox
    object_rows.append(
        {
            "object": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId,
            "solids": len(shape.Solids),
            "faces": len(shape.Faces),
            "edges": len(shape.Edges),
            "xmin_mm": bb.XMin,
            "ymin_mm": bb.YMin,
            "zmin_mm": bb.ZMin,
            "xmax_mm": bb.XMax,
            "ymax_mm": bb.YMax,
            "zmax_mm": bb.ZMax,
            "xlen_mm": bb.XLength,
            "ylen_mm": bb.YLength,
            "zlen_mm": bb.ZLength,
        }
    )

    for idx, face in enumerate(shape.Faces, start=1):
        try:
            surf = face.Surface
        except Exception:
            continue
        if isinstance(surf, Part.Cylinder):
            center = surf.Center
            axis = surf.Axis
            bb_f = face.BoundBox
            cylinder_rows.append(
                {
                    "object": obj.Name,
                    "label": obj.Label,
                    "face_index": idx,
                    "radius_mm": surf.Radius,
                    "center_x_mm": center.x,
                    "center_y_mm": center.y,
                    "center_z_mm": center.z,
                    "axis_x": unit_tuple(axis)[0],
                    "axis_y": unit_tuple(axis)[1],
                    "axis_z": unit_tuple(axis)[2],
                    "bbox_xmin_mm": bb_f.XMin,
                    "bbox_ymin_mm": bb_f.YMin,
                    "bbox_zmin_mm": bb_f.ZMin,
                    "bbox_xmax_mm": bb_f.XMax,
                    "bbox_ymax_mm": bb_f.YMax,
                    "bbox_zmax_mm": bb_f.ZMax,
                    "bbox_xlen_mm": bb_f.XLength,
                    "bbox_ylen_mm": bb_f.YLength,
                    "bbox_zlen_mm": bb_f.ZLength,
                }
            )

    for idx, edge in enumerate(shape.Edges, start=1):
        try:
            curve = edge.Curve
        except Exception:
            continue
        if isinstance(curve, Part.Circle):
            center = curve.Center
            axis = curve.Axis
            bb_e = edge.BoundBox
            circle_rows.append(
                {
                    "object": obj.Name,
                    "label": obj.Label,
                    "edge_index": idx,
                    "radius_mm": curve.Radius,
                    "center_x_mm": center.x,
                    "center_y_mm": center.y,
                    "center_z_mm": center.z,
                    "axis_x": unit_tuple(axis)[0],
                    "axis_y": unit_tuple(axis)[1],
                    "axis_z": unit_tuple(axis)[2],
                    "bbox_xmin_mm": bb_e.XMin,
                    "bbox_ymin_mm": bb_e.YMin,
                    "bbox_zmin_mm": bb_e.ZMin,
                    "bbox_xmax_mm": bb_e.XMax,
                    "bbox_ymax_mm": bb_e.YMax,
                    "bbox_zmax_mm": bb_e.ZMax,
                    "bbox_xlen_mm": bb_e.XLength,
                    "bbox_ylen_mm": bb_e.YLength,
                    "bbox_zlen_mm": bb_e.ZLength,
                }
            )

write_csv(
    OUT_OBJECTS,
    object_rows,
    [
        "object",
        "label",
        "type",
        "solids",
        "faces",
        "edges",
        "xmin_mm",
        "ymin_mm",
        "zmin_mm",
        "xmax_mm",
        "ymax_mm",
        "zmax_mm",
        "xlen_mm",
        "ylen_mm",
        "zlen_mm",
    ],
)
write_csv(
    OUT_CYLINDERS,
    cylinder_rows,
    [
        "object",
        "label",
        "face_index",
        "radius_mm",
        "center_x_mm",
        "center_y_mm",
        "center_z_mm",
        "axis_x",
        "axis_y",
        "axis_z",
        "bbox_xmin_mm",
        "bbox_ymin_mm",
        "bbox_zmin_mm",
        "bbox_xmax_mm",
        "bbox_ymax_mm",
        "bbox_zmax_mm",
        "bbox_xlen_mm",
        "bbox_ylen_mm",
        "bbox_zlen_mm",
    ],
)
write_csv(
    OUT_CIRCLES,
    circle_rows,
    [
        "object",
        "label",
        "edge_index",
        "radius_mm",
        "center_x_mm",
        "center_y_mm",
        "center_z_mm",
        "axis_x",
        "axis_y",
        "axis_z",
        "bbox_xmin_mm",
        "bbox_ymin_mm",
        "bbox_zmin_mm",
        "bbox_xmax_mm",
        "bbox_ymax_mm",
        "bbox_zmax_mm",
        "bbox_xlen_mm",
        "bbox_ylen_mm",
        "bbox_zlen_mm",
    ],
)

print(f"STEP: {STEP_PATH}")
print(f"objects: {len(object_rows)} -> {OUT_OBJECTS}")
print(f"cylinders: {len(cylinder_rows)} -> {OUT_CYLINDERS}")
print(f"circles: {len(circle_rows)} -> {OUT_CIRCLES}")
