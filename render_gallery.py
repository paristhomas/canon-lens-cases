"""Gallery renders for the README and model pages -> docs/img/gallery/*.png (1600 x 1200).

usage: python render_gallery.py      (after build_all.py)
"""
import json
from pathlib import Path

import numpy as np
import pyvista as pv

import render as R

MP = Path("out/manifest.json").resolve()
MAN = json.loads(MP.read_text())
OUT = Path("docs/img/gallery")
SIZE = (1600, 1200)
BG = "#f2f2f0"
BODY, LID, RING = "#33373d", "#e07a2f", "#8a8f96"
LENS = "#6b6f75"


def variant(name):
    return next(v for v in MAN["variants"] if v["name"] == name)


def rz(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])


def move(dx=0.0, dy=0.0, dz=0.0):
    m = np.eye(4)
    m[:3, 3] = dx, dy, dz
    return m


def meshes(name, pose=0, lift=0.0, turn=0.0, contents=False, hide=(), lens_lift=0.0):
    """[(mesh, colour)] for one variant: lid / top tube lifted and turned if asked; with
    contents, the lens and its caps (no foam) lifted by lens_lift."""
    v = variant(name)
    p = v["poses"][pose]
    out = []
    for part, m in R.assemble(MP, v, p):
        if part in hide:
            continue
        if part in ("lid", "inner"):
            m.apply_transform(move(dz=lift) @ rz(turn))
        out.append((m, {"body": BODY, "ring": RING}.get(part, LID)))
    if contents:
        for _, kind, m in R.visuals(MP, p):
            if kind != "foam":
                out.append((m.apply_transform(move(dz=lens_lift)), LENS))
    return out


def shot(items, path, az, el, dist, focus, angle=26, up=(0, 0, 1), headlight=0.0):
    pl = pv.Plotter(off_screen=True, window_size=SIZE)
    pl.set_background(BG)
    for m, c in items:
        pl.add_mesh(pv.wrap(m), color=c, smooth_shading=True, split_sharp_edges=True,
                    specular=0.25, specular_power=20, diffuse=0.85, ambient=0.12)
    a, e = np.radians(az), np.radians(el)
    f = np.array(focus, float)
    pl.camera.focal_point = f
    pl.camera.position = f + dist * np.array([np.cos(a) * np.cos(e), np.sin(a) * np.cos(e), np.sin(e)])
    pl.camera.up = up
    pl.camera.view_angle = angle
    if headlight:                  # faces turned away from the light kit (the base)
        pl.add_light(pv.Light(light_type="headlight", intensity=headlight))
    pl.enable_anti_aliasing("ssaa")
    pl.screenshot(str(path))
    pl.close()
    print(path)


def placed(items, dx, dy=0.0):
    return [(m.copy().apply_transform(move(dx, dy)), c) for m, c in items]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # 1. the set, shortest to tallest, case 1 extended at the end
    row, x = [], 0.0
    for name, pose in (("case2_bayonet", 0), ("case4_bayonet", 0), ("case6_bayonet", 0),
                       ("case5_bayonet", 0), ("case3_bayonet", 0), ("case1_bayonet", 4)):
        row += placed(meshes(name, pose), x)
        x += 115
    shot(row, OUT / "set.png", -90, 12, 1550, (x / 2 - 57.5, 0, 95), angle=20)
    # 2. case 1 collapsed and extended
    shot(placed(meshes("case1_bayonet", 0), -60) + placed(meshes("case1_bayonet", 4), 60),
         OUT / "case1_positions.png", -80, 15, 470, (0, 0, 75))
    # 3. lens going in: case 5 open, lid lifted, lens and caps shown (no foam)
    shot(meshes("case5_bayonet", contents=True, lift=175, turn=25, lens_lift=120), OUT / "case5_open.png",
         -60, 10, 860, (0, 0, 175))
    # 4. closing: the lid set on the body, before the push and twist
    shot(meshes("case2_bayonet", lift=14, turn=25), OUT / "entry_mark.png", 70, 12, 250, (0, 0, 58))
    # 5. top: lock arrow
    shot(meshes("case4_bayonet"), OUT / "top.png", -90, 75, 240, (0, 0, 100))
    # 6. base: lens details
    shot(meshes("case5_bayonet"), OUT / "base.png", -90, -72, 240, (0, 0, 5), up=(0, -1, 0), headlight=0.6)
    # 7. lead-in crown inside the case 1 body rim
    shot(meshes("case1_bayonet", hide=("inner",)), OUT / "case1_lead_in.png", 250, 45, 280, (0, 0, 75))


if __name__ == "__main__":
    main()
