"""Magnified cross-sections of every joint with the printed gaps measured and dimensioned.

Reads out/manifest.json + STLs (like verify.py), cuts each assembly through the XZ plane,
crops to the joint, and labels the local minimum gaps between different parts.
Writes out/renders/gaps_<joint>.png and out/renders/gaps.png (all four).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union

import verify as V

COLORS = {"body": "#3f6d9e", "lid": "#d9822b", "inner": "#d9822b", "ring": "#4f9a63"}
NAMES = {"body": "body", "lid": "lid", "inner": "top tube", "ring": "lock ring"}


def section(mesh):
    sec = mesh.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    polys = []
    for ent in sec.discrete:
        p = Polygon(ent[:, [0, 2]]).buffer(0)
        if not p.is_empty:
            polys.append(p)
    g = polys[0]
    for p in polys[1:]:
        g = g.symmetric_difference(p)
    return g


def gaps(ga, gb, win, max_gap=1.5, spacing=1.6, n=6, skip_vertical=False):
    """Local-minimum gaps from part a's boundary to part b inside the window."""
    a, b = ga.intersection(win), gb.intersection(win)
    if a.is_empty or b.is_empty:
        return []
    line = a.boundary
    pts = [line.interpolate(d) for d in np.arange(0, line.length, 0.03)]
    cand = []
    for p in pts:
        d = b.distance(p)
        if 0.15 < d < max_gap:                     # below this = seated stop (contact by design)
            cand.append((d, p))
    cand.sort(key=lambda t: t[0])
    picked = []
    for d, p in cand:
        if all(p.distance(q) > spacing for _, q, _ in picked):
            q = nearest_points(p, b)[1]
            if skip_vertical and abs(q.y - p.y) > 0.9 * d:   # axial seating stop, not a fit
                continue
            picked.append((d, p, q))
        if len(picked) >= n:
            break
    return picked


def panel(ax, mp, v, pose_idx, win_xz, title, notes, skip_vertical=False):
    pose = v["poses"][pose_idx]
    parts = V.assemble(mp, v, pose)
    x0, x1, z0, z1 = win_xz
    win = box(x0, z0, x1, z1)
    geo = {n: section(m) for n, m in parts}
    for n, g in geo.items():
        gg = g.intersection(win.buffer(2))
        for poly in getattr(gg, "geoms", [gg]):
            if poly.geom_type != "Polygon":
                continue
            ax.fill(*poly.exterior.xy, color=COLORS.get(n, "#888"), alpha=0.92, lw=0.6, ec="#1b2026",
                    label=NAMES.get(n, n))
            for hole in poly.interiors:
                ax.fill(*hole.xy, color="white", lw=0.6, ec="#1b2026")
    names = list(geo)
    found = []
    stops = [sorted(p) for p in v.get("stop_pairs", [])]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if sorted([names[i], names[j]]) not in stops:
                found += gaps(geo[names[i]], geo[names[j]], win, skip_vertical=skip_vertical)
    for d, p, q in found:
        ax.annotate("", xy=(q.x, q.y), xytext=(p.x, p.y),
                    arrowprops=dict(arrowstyle="<->", color="#c0262d", lw=1.1, shrinkA=0, shrinkB=0))
        mx, mz = (p.x + q.x) / 2, (p.y + q.y) / 2
        ax.text(mx + 0.25, mz + 0.2, f"{d:.2f}", color="#c0262d", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    ax.set_xlim(x0, x1); ax.set_ylim(z0, z1); ax.set_aspect("equal")
    ax.set_xticks(np.arange(np.ceil(x0), x1, 1)); ax.set_yticks(np.arange(np.ceil(z0), z1, 1))
    ax.grid(True, color="#dfe3e8", lw=0.5); ax.tick_params(labelsize=7)
    ax.set_xlabel("radius (mm)", fontsize=8); ax.set_ylabel("height (mm)", fontsize=8)
    ax.set_title(title, fontsize=10, loc="left", fontweight="bold")
    h, l = ax.get_legend_handles_labels()
    uniq = dict(zip(l, h))
    ax.legend(uniq.values(), uniq.keys(), fontsize=7, loc="upper left", framealpha=0.9)
    ax.text(0.99, 0.01, notes, transform=ax.transAxes, fontsize=7.5, ha="right", va="bottom",
            color="#3a434d", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#d3d8de", alpha=0.92))
    return [d for d, _, _ in found]


def find(man, name):
    return next(v for v in man["variants"] if v["name"] == name)


def main():
    mp = Path("out/manifest.json").resolve()
    man = json.loads(mp.read_text())
    import params as P
    out = Path("out/renders"); out.mkdir(parents=True, exist_ok=True)

    def window(v, pose_idx, zc_frac, rpad=(4, 3), zh=12):
        """Window around the joint: radial span of the parts' outer walls, z around zc."""
        parts = V.assemble(mp, v, v["poses"][pose_idx])
        bounds = np.vstack([m.bounds for _, m in parts])
        r_out = bounds[:, 0].max()
        return r_out, zc_frac

    specs = []
    # fixed bayonet: pin at angle 0 sits in the hook notch near the body rim
    v = find(man, "case2_bayonet")
    r = v["envelope"]["od"] / 2
    zt = v["envelope"]["length"]
    rim = zt - (P.END_CAP + P.LABEL_DEPTH) - P.BAYONET_NOTCH
    specs.append(("bayonet_fixed", v, 0, (r - 8.5, r + 0.8, rim - 9, rim + 3),
                  "A. Bayonet pin in the lid's J-slot (fixed cases)",
                  f"pin {P.PIN_WIDTH:.0f} x {P.PIN_HEIGHT:.0f} mm, hooks {P.GROOVE_DEPTH - P.PIN_RADIAL_GAP:.1f} mm past the lid wall\n"
                  f"set: {P.SLIDE_CLEAR} radial, {P.PIN_RADIAL_GAP} at tip, {P.PIN_AXIAL_CLEAR} axial"))
    v = find(man, "case2_threaded")
    r = v["envelope"]["od"] / 2
    rim = v["envelope"]["length"] - (P.END_CAP + P.LABEL_DEPTH)
    specs.append(("thread_fixed", v, 0, (r - 9, r + 0.8, rim - 15, rim + 2),
                  "B. Lid thread (fixed cases)",
                  f"pitch {P.THREAD_PITCH:.0f} mm, depth {P.THREAD_DEPTH} mm, 45 deg flanks\n"
                  f"set: {P.THREAD_CLEAR} radial crest/root, {P.THREAD_FLANK_GAP} axial on flanks\n"
                  "lid ceiling seats on the body rim (contact by design)"))
    v = find(man, "case1_bayonet")
    r = v["envelope"]["od"] / 2
    specs.append(("bayonet_tele", v, 1, (r - 10, r + 0.8, 26, 40),
                  "C. Telescoping J-track, position 2",
                  f"top tube slides in the body: {P.SLIDE_CLEAR} radial\npin in notch: {P.PIN_AXIAL_CLEAR} axial, {P.PIN_RADIAL_GAP} at tip"))
    v = find(man, "case1_threaded")
    r = v["envelope"]["od"] / 2
    specs.append(("thread_tele", v, 0, (r - 9.5, r + 0.8, 70, 92),
                  "D. Telescoping thread + lock ring, position 1",
                  f"2-start, lead {P.THREAD_PITCH * P.TELE_THREAD_STARTS:.0f} mm; ring jams on the body rim\n"
                  f"set: {P.THREAD_CLEAR} radial, {P.THREAD_FLANK_GAP} axial on flanks\n"
                  "ring seats on the body rim (contact by design)"))

    fig_all, axs = plt.subplots(2, 2, figsize=(13, 12), dpi=110)
    summary = {}
    for (key, v, pi, win, title, notes), ax in zip(specs, axs.flat):
        sv = key == "thread_fixed"
        found = panel(ax, mp, v, pi, win, title, notes, sv)
        summary[key] = (min(found) if found else None, max(found) if found else None)
        f1, a1 = plt.subplots(figsize=(7, 7), dpi=130)
        panel(a1, mp, v, pi, win, title, notes, sv)
        f1.tight_layout(); f1.savefig(out / f"gaps_{key}.png"); plt.close(f1)
    fig_all.suptitle(f"Printed gaps between mating parts (mm, measured on the exported meshes; "
                     f"minimum allowed {P.MIN_PRINT_GAP})", fontsize=11, x=0.01, ha="left")
    fig_all.tight_layout(); fig_all.savefig(out / "gaps.png"); plt.close(fig_all)
    for k, (lo, hi) in summary.items():
        print(f"{k:15s} gaps {lo:.2f} - {hi:.2f} mm" if lo else f"{k}: none found")


if __name__ == "__main__":
    main()
