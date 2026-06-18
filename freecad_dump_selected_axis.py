import FreeCADGui as Gui


def vec(v):
    return f"({v.x:.12f}, {v.y:.12f}, {v.z:.12f})"


sel = Gui.Selection.getSelectionEx()
if not sel:
    raise SystemExit("No selection. Select a cylindrical motor/shaft surface first.")

s = sel[0]
if not s.SubObjects:
    raise SystemExit("Selection has no subobject. Select a face, not just the tree item.")

sub = s.SubObjects[0]
if not hasattr(sub, "Surface"):
    raise SystemExit("Selected subobject has no Surface. Select a cylindrical face.")

surf = sub.Surface
if not all(hasattr(surf, name) for name in ("Center", "Axis", "Radius")):
    raise SystemExit("Selected surface is not a cylinder-like surface with Center/Axis/Radius.")

print("Object    =", s.ObjectName)
print("SubObject =", s.SubElementNames[0] if s.SubElementNames else "<unknown>")
print("Center    =", vec(surf.Center))
print("Axis      =", vec(surf.Axis))
print("Radius    =", f"{surf.Radius:.12f}")
