"""Render lens-case variants from out/manifest.json + STLs (no CAD imports).

usage: python render.py [--manifest path] [--outdir out/renders] [--only substring] [--matplotlib]
Writes {name}_iso.png, _exploded.png, _cutaway.png, _section.png.
iso/exploded/cutaway use pyvista (VTK, off-screen) when available, else a matplotlib fallback.
"""
import argparse
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MPath
from shapely.geometry import Polygon

PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2", "#9D755D"]
BG = "#F4F5F7"
SIZE = (1400, 900)
MAX_FACES = 150_000
CUT_Y = 0.001   # section plane offset: avoids vertices lying exactly on the plane


def T(v):
    return np.array(v, float).reshape(4, 4)


def resolve(mp, p):
    p = Path(p)
    for c in (p, Path.cwd() / p, mp.parent / p, mp.parent.parent / p, mp.parent / p.name):
        if c.exists():
            return c
    raise FileNotFoundError(p)


_cache = {}


def load(mp, rel):
    if rel not in _cache:
        m = trimesh.load(resolve(mp, rel), force="mesh", process=True)
        if m.is_watertight and m.volume < 0:
            m.invert()
        _cache[rel] = m
    return _cache[rel]


def assemble(mp, v, pose=None, explode=False):
    out = []
    for p in v["parts"]:
        m = load(mp, p["stl"]).copy()
        M = T(p["to_use"])
        if pose is not None and p["name"] in pose.get("transforms", {}):
            M = T(pose["transforms"][p["name"]]) @ M
        if explode and p["name"] in v.get("explode", {}):
            M = T(v["explode"][p["name"]]) @ M
        m.apply_transform(M)
        out.append((p["name"], m))
    return out


def visuals(mp, pose):
    """[(name, kind, mesh)] non-printed contents (foam / lens) already in the assembled frame."""
    out = []
    for x in (pose or {}).get("visual", []):
        try:
            out.append((x["name"], x.get("kind", "foam"), load(mp, x["stl"]).copy()))
        except Exception as e:  # noqa
            print("   visual load failed:", x.get("stl"), e)
    return out


FOAM_RGB, LENS_RGB = "#F2D16B", "#9AA0A6"


def color_of(v, name):
    return PALETTE[[p["name"] for p in v["parts"]].index(name) % len(PALETTE)]


def floor_top(parts):
    comb = trimesh.util.concatenate([m for _, m in parts])
    z0 = comb.bounds[0][2] - 1
    loc, _, _ = comb.ray.intersects_location([[0.0013, 0.0029, z0]], [[0, 0, 1.0]], multiple_hits=True)
    z = np.sort(loc[:, 2])
    return float(z[1]) if len(z) >= 2 else 0.0


# ------------------------------------------------------------------ 3D panels
def cutaway(parts):
    out = []
    for n, m in parts:
        try:
            c = trimesh.intersections.slice_mesh_plane(m, [0, 1, 0], [0, CUT_Y, 0], cap=True)
        except Exception as e:  # noqa
            print("   cutaway failed for", n, e)
            continue
        if c is not None and len(c.faces):
            out.append((n, c))
    return out


def decimate(parts):
    tot = sum(len(m.faces) for _, m in parts)
    if tot <= MAX_FACES:
        return parts
    ratio = MAX_FACES / tot
    out = []
    for n, m in parts:
        try:
            out.append((n, m.simplify_quadric_decimation(percent=1 - ratio)))
        except Exception:  # noqa
            out.append((n, m))
    return out


def render_pyvista(panels, path, view):
    import pyvista as pv
    pv.OFF_SCREEN = True
    pl = pv.Plotter(off_screen=True, shape=(1, len(panels)), window_size=(max(SIZE[0], 650 * len(panels)), SIZE[1]), border=False)
    pl.set_background(BG)
    for i, (title, parts, colors) in enumerate(panels):
        pl.subplot(0, i)
        lo = np.min([m.bounds[0] for _, m in parts], 0)
        hi = np.max([m.bounds[1] for _, m in parts], 0)
        c = (lo + hi) / 2
        D = float(np.linalg.norm(hi - lo))
        pl.enable_depth_peeling(10)
        for n, m in decimate(parts):
            pd = pv.wrap(m)
            pd = pd.compute_normals(split_vertices=True, feature_angle=35, cell_normals=False, inplace=False)
            col = colors[n]
            col, op = col if isinstance(col, tuple) else (col, 1.0)
            pl.add_mesh(pd, color=col, opacity=op, smooth_shading=True, specular=0.25, specular_power=20)
        d = np.array([-0.55, -1.0, 0.55]) if view == "cut" else np.array([1.0, -1.1, 0.8])
        pl.camera_position = [tuple(c + d / np.linalg.norm(d) * D * 2.2), tuple(c), (0, 0, 1)]
        pl.reset_camera()
        pl.camera.zoom(1.1 if view == "cut" else 0.95)
        pl.add_text(title, font_size=11, color="#222222", position="upper_left")
        pl.add_axes(line_width=2, color="#444444")
    pl.screenshot(str(path))
    pl.close()


def render_mpl3d(panels, path, view):
    from matplotlib.colors import to_rgb
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(SIZE[0] / 100, SIZE[1] / 100), dpi=100, facecolor=BG)
    elev, azim = (20, -65) if view == "cut" else (25, 40)
    az, el = np.radians(azim), np.radians(elev)
    vdir = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])   # towards viewer
    light = vdir * 0.6 + np.array([0.3, -0.3, 0.7])
    light /= np.linalg.norm(light)
    for i, (title, parts, colors) in enumerate(panels):
        ax = fig.add_subplot(1, len(panels), i + 1, projection="3d", facecolor=BG)
        allv = np.vstack([m.vertices for _, m in parts])
        lo, hi = allv.min(0), allv.max(0)
        c = (lo + hi) / 2
        h = (hi - lo).max() / 2
        polys, cols, depth = [], [], []
        for n, m in decimate(parts):
            fn = m.face_normals
            tri = m.vertices[m.faces]
            vis = fn @ vdir > -0.05
            shade = 0.35 + 0.65 * np.clip(fn @ light, 0, 1)
            base = np.array(to_rgb(colors[n][0] if isinstance(colors[n], tuple) else colors[n]))
            for t, s in zip(tri[vis], shade[vis]):
                polys.append(t)
                cols.append(np.clip(base * s, 0, 1))
            depth.extend((tri[vis].mean(1) @ vdir).tolist())
        order = np.argsort(depth)
        pc = Poly3DCollection([polys[k] for k in order], facecolors=[cols[k] for k in order],
                              edgecolors="none", linewidths=0)
        ax.add_collection3d(pc)
        ax.set_xlim(c[0] - h, c[0] + h); ax.set_ylim(c[1] - h, c[1] + h); ax.set_zlim(c[2] - h, c[2] + h)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev, azim)
        ax.set_axis_off()
        ax.set_title(title, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, facecolor=BG)
    plt.close(fig)


# ------------------------------------------------------------------ section
def section_polys(mesh):
    sec = mesh.section(plane_origin=[0, CUT_Y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return None
    polys = []
    for loop in sec.discrete:
        xy = loop[:, [0, 2]]
        if len(xy) >= 4:
            p = Polygon(xy).buffer(0)
            if not p.is_empty:
                polys.append(p)
    if not polys:
        return None
    geom = polys[0]
    for p in polys[1:]:
        geom = geom.symmetric_difference(p)   # even-odd: holes become holes
    return geom


def patch_for(geom, **kw):
    geoms = getattr(geom, "geoms", [geom])
    verts, codes = [], []
    for g in geoms:
        if g.geom_type != "Polygon":
            continue
        for ring in [g.exterior, *g.interiors]:
            xy = np.asarray(ring.coords)
            verts.extend(xy)
            codes.extend([MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY])
    return PathPatch(MPath(verts, codes), **kw)


def render_section(mp, v, path):
    poses = v.get("poses") or [dict(name="closed", req_len=0, req_dia=0, transforms={})]
    sets = [assemble(mp, v, p) for p in poses]
    allb = np.vstack([m.bounds for s in sets for _, m in s])
    for p in poses:
        for _, _, vm in visuals(mp, p):
            allb = np.vstack([allb, vm.bounds])
    zlo, zhi = allb[:, 2].min() - 3, allb[:, 2].max() + 3
    xr = max(abs(allb[:, 0]).max(), max(p.get("req_dia", 0) for p in poses) / 2) + 4
    n = len(poses)
    fig, axes = plt.subplots(1, n, figsize=(SIZE[0] / 100, SIZE[1] / 100), dpi=100, facecolor=BG, squeeze=False)
    for ax, pose, parts in zip(axes[0], poses, sets):
        ax.set_facecolor("white")
        seen = set()
        for vn, kind, vm in visuals(mp, pose):
            g = section_polys(vm)
            if g is None:
                continue
            if kind == "lens":
                lab = None if "lens" in seen else "lens + caps (spec envelope proxy)"
                seen.add("lens")
                ax.add_patch(patch_for(g, facecolor=LENS_RGB, edgecolor="#4A4F55", linewidth=0.9, alpha=0.9,
                                       label=lab, zorder=3))
            else:
                lab = None if "foam" in seen else "foam (3 mm radial, 8 mm bottom, 5 mm top)"
                seen.add("foam")
                ax.add_patch(patch_for(g, facecolor=FOAM_RGB, edgecolor="#B8962E", linewidth=0.5, alpha=0.55,
                                       hatch="///", label=lab, zorder=1))
        for name, m in parts:
            g = section_polys(m)
            if g is not None:
                ax.add_patch(patch_for(g, facecolor=color_of(v, name), edgecolor="#222", linewidth=0.7, alpha=0.9,
                                       label=name, zorder=2))
        ft = floor_top(parts)
        if pose.get("req_dia"):
            ax.add_patch(Rectangle((-pose["req_dia"] / 2, ft), pose["req_dia"], pose["req_len"], fill=False,
                                   linestyle="--", edgecolor="#C00000", linewidth=1.6, zorder=4,
                                   label=f"lens envelope {pose['req_dia']:.1f} x {pose['req_len']:.1f}"))
        ax.axvline(0, color="#888", linewidth=0.6, linestyle="-.")
        ax.set_xlim(-xr, xr); ax.set_ylim(zlo, zhi)
        ax.set_aspect("equal")
        ax.set_xticks(np.arange(np.ceil(-xr / 10) * 10, xr, 10))
        ax.set_yticks(np.arange(np.floor(zlo / 10) * 10, zhi, 10))
        ax.grid(True, color="#DDD", linewidth=0.5)
        ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm)")
        t = f"{v.get('title', v['name'])}\npose: {pose['name']}"
        if pose.get("req_len"):
            t += f"  (req {pose['req_dia']:.1f} x {pose['req_len']:.1f}, target {pose.get('target_len', 0):.1f})"
        ax.set_title(t, fontsize=9, loc="left")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path, facecolor=BG)
    plt.close(fig)


# ------------------------------------------------------------------ driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/manifest.json")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--only", default="")
    ap.add_argument("--matplotlib", action="store_true", help="force matplotlib 3D fallback")
    a = ap.parse_args()
    mp = Path(a.manifest).resolve()
    man = json.loads(mp.read_text())
    outdir = Path(a.outdir) if a.outdir else mp.parent / "renders"
    outdir.mkdir(parents=True, exist_ok=True)
    r3d = render_mpl3d
    if not a.matplotlib:
        try:
            import pyvista  # noqa
            r3d = render_pyvista
        except Exception as e:  # noqa
            print("pyvista unavailable, using matplotlib:", e)
    t0 = time.time()
    for v in man["variants"]:
        if a.only not in v["name"]:
            continue
        t = time.time()
        name = v["name"]
        poses = v.get("poses") or [None]
        shown = [poses[0]] + ([poses[-1]] if v["kind"] == "telescoping" and len(poses) > 1 else [])
        colors = {p["name"]: color_of(v, p["name"]) for p in v["parts"]}
        panels = [(f"{v.get('title', name)} - {p['name'] if p else 'closed'}", assemble(mp, v, p), colors)
                  for p in shown]
        r3d(panels, outdir / f"{name}_iso.png", "iso")
        ex = [(f"{v.get('title', name)} - exploded", assemble(mp, v, None, explode=True), colors)]
        r3d(ex, outdir / f"{name}_exploded.png", "iso")
        cp = [(f"{t} (cutaway)", cutaway(parts), colors) for t, parts, _ in panels]
        r3d([c for c in cp if c[1]], outdir / f"{name}_cutaway.png", "cut")
        # contents: cutaway with foam + lens, every pose
        cpan = []
        for p in poses:
            parts = cutaway(assemble(mp, v, p))
            col = dict(colors)
            for vn, kind, vm in visuals(mp, p):
                try:
                    c = trimesh.intersections.slice_mesh_plane(vm, [0, 1, 0], [0, CUT_Y, 0], cap=True)
                except Exception as e:  # noqa
                    print("   visual cut failed", vn, e)
                    continue
                if c is not None and len(c.faces):
                    key = "vis:" + vn
                    parts.append((key, c))
                    col[key] = (FOAM_RGB, 0.45) if kind == "foam" else (LENS_RGB, 1.0)
            cpan.append((f"{v.get('title', name)} - {p['name'] if p else 'closed'} (contents)", parts, col))
        r3d([c for c in cpan if c[1]], outdir / f"{name}_contents.png", "cut")
        render_section(mp, v, outdir / f"{name}_section.png")
        print(f"{name}: 5 images in {time.time() - t:.1f}s")
    print(f"done in {time.time() - t0:.1f}s -> {outdir}")


if __name__ == "__main__":
    main()
