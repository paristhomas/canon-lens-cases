"""Verification of lens-case STLs. Reads only out/manifest.json + listed STLs.

usage: python verify.py [--manifest path]      exit code 1 on any FAIL
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

JIT = (0.00137, 0.00291)   # tiny offset so rays never run exactly along mesh edges / axis vertices
fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print("  FAIL: " + msg)


def warn(msg):
    warns.append(msg)
    print("  warn: " + msg)


# ---------------------------------------------------------------- loading
def resolve(manifest_path, p):
    p = Path(p)
    for c in (p, Path.cwd() / p, manifest_path.parent / p, manifest_path.parent.parent / p,
              manifest_path.parent / p.name):
        if c.exists():
            return c
    raise FileNotFoundError(f"{p} (manifest {manifest_path})")


_cache = {}


def load_mesh(manifest_path, rel):
    key = str(rel)
    if key not in _cache:
        m = trimesh.load(resolve(manifest_path, rel), force="mesh", process=True)
        if m.is_watertight and m.volume < 0:
            m.invert()
        _cache[key] = m
    return _cache[key]


def T(v):
    return np.array(v, float).reshape(4, 4)


def assemble(manifest_path, variant, pose=None, explode=False):
    """List of (partname, transformed mesh copy): to_use, then pose transform (or explode transform)."""
    out = []
    for p in variant["parts"]:
        m = load_mesh(manifest_path, p["stl"]).copy()
        M = T(p["to_use"])
        if pose is not None and p["name"] in pose.get("transforms", {}):
            M = T(pose["transforms"][p["name"]]) @ M
        if explode and p["name"] in variant.get("explode", {}):
            M = T(variant["explode"][p["name"]]) @ M
        m.apply_transform(M)
        out.append((p["name"], m))
    return out


# ---------------------------------------------------------------- ray utils
def cast(mesh, origins, dirs, batch=20000):
    """Per ray: (t sorted, sign) with sign +1 entering material, -1 leaving."""
    n = len(origins)
    res = [None] * n
    empty = (np.zeros(0), np.zeros(0, int))
    fn = mesh.face_normals
    for s in range(0, n, batch):
        o = origins[s:s + batch]
        d = dirs[s:s + batch]
        loc, ir, it = mesh.ray.intersects_location(o, d, multiple_hits=True)
        if len(ir):
            t = np.einsum("ij,ij->i", loc - o[ir], d[ir])
            sg = np.where(np.einsum("ij,ij->i", fn[it], d[ir]) < 0, 1, -1)
            order = np.lexsort((t, ir))
            ir, t, sg = ir[order], t[order], sg[order]
            bounds = np.flatnonzero(np.diff(ir)) + 1
            starts = np.r_[0, bounds]
            ends = np.r_[bounds, len(ir)]
            for a, b in zip(starts, ends):
                res[s + ir[a]] = (t[a:b], sg[a:b])
        for i in range(len(o)):
            if res[s + i] is None:
                res[s + i] = empty
    return res


def intervals(t, sg, merge=1e-4):
    """Material intervals along a ray: list of (a, b, starts_inside_material).
    Depth counting copes with overlapping parts and duplicate edge hits."""
    if len(t) == 0:
        return []
    d0 = 1 if sg[0] < 0 else 0          # first crossing is an exit -> origin was inside material
    depth = d0 + np.cumsum(sg)
    out = []
    cur = 0.0 if d0 else None
    prev = d0
    for ti, di in zip(t, depth):
        if prev <= 0 < di:
            cur = ti
        elif prev > 0 >= di and cur is not None:
            if out and cur - out[-1][1] < merge:
                out[-1] = (out[-1][0], ti, out[-1][2])
            else:
                out.append((cur, ti, bool(d0) and not out))
            cur = None
        prev = di
    return out


def rays_radial(z, thetas):
    Z, TH = np.meshgrid(np.asarray(z, float), thetas, indexing="ij")
    Z = Z.ravel()
    TH = TH.ravel()
    d = np.stack([np.cos(TH), np.sin(TH), np.zeros_like(TH)], 1)
    o = np.stack([np.full_like(Z, JIT[0]), np.full_like(Z, JIT[1]), Z], 1)
    return o, d, Z, TH


def rays_vertical(xy, z0):
    xy = np.asarray(xy, float).reshape(-1, 2)
    o = np.column_stack([xy[:, 0] + JIT[0], xy[:, 1] + JIT[1], np.full(len(xy), z0)])
    d = np.tile([0.0, 0.0, 1.0], (len(xy), 1))
    return o, d


# ---------------------------------------------------------------- 1/2 fit
def measure_fit(meshes):
    comb = trimesh.util.concatenate([m for _, m in meshes])
    zlow = comb.bounds[0][2] - 1.0
    o, d = rays_vertical([[0, 0]], zlow)
    iv = intervals(*cast(comb, o, d)[0])
    if len(iv) < 2:
        return None
    floor_top, ceil0 = iv[0][1] + zlow, iv[1][0] + zlow
    if ceil0 - floor_top > 1.5:
        # odd offset so no sample plane lands exactly on a flat face (rim tops sit on 0.1 mm values)
        zs = np.linspace(floor_top + 0.5, ceil0 - 0.5, int(min(120, max(5, ceil0 - floor_top)))) + 0.0137
    else:
        zs = np.array([(floor_top + ceil0) / 2])
    th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    o, d, Z, TH = rays_radial(zs, th)
    rad = np.full(len(o), np.inf)
    for i, (t, sg) in enumerate(cast(comb, o, d)):
        v = intervals(t, sg)
        if v:
            rad[i] = 0.0 if v[0][2] else v[0][0]
    k = int(np.argmin(rad))
    rmin = float(rad[k])
    pts = [[0, 0]]
    for r in (5, 15, 25):
        if r < rmin - 0.5:
            pts += [[r * math.cos(a), r * math.sin(a)] for a in np.radians(np.arange(0, 360, 45))]
    o, d = rays_vertical(pts, zlow)
    lens = []
    for t, sg in cast(comb, o, d):
        v = intervals(t, sg)
        if len(v) >= 2:
            lens.append(v[1][0] - v[0][1])
    return dict(length=min(lens), dia=2 * rmin, floor_top=float(floor_top),
                dia_at=(float(Z[k]), float(np.degrees(TH[k]))))


def check_fit(mp, man):
    P = man["params"]
    print("\n=== 1/2. FIT TABLE (measured on assembled meshes) ===")
    hdr = (f"{'variant':<22}{'pose':<26}{'reqL':>7}{'measL':>8}{'dL':>7}"
           f"{'reqD':>7}{'measD':>8}{'dD':>7}  note")
    print(hdr)
    print("-" * len(hdr))
    TOL = 0.01
    for v in man["variants"]:
        poses = v.get("poses") or [dict(name="closed", req_len=0, req_dia=0, transforms={})]
        for pose in poses:
            r = measure_fit(assemble(mp, v, pose))
            tag = f"{v['name']} / {pose['name']}"
            if r is None:
                print(f"{v['name']:<22}{pose['name'][:25]:<26} could not find floor+ceiling on the axis")
                fail(f"{tag}: no floor/ceiling found on axis")
                continue
            dl = r["length"] - pose["req_len"]
            dd = r["dia"] - pose["req_dia"]
            note = []
            if dl < -TOL:
                note.append("FAIL len")
                fail(f"{tag}: interior length {r['length']:.2f} < required {pose['req_len']:.2f}")
            if dd < -TOL:
                note.append(f"FAIL dia (min r at z={r['dia_at'][0]:.1f}, {r['dia_at'][1]:.0f}deg)")
                fail(f"{tag}: interior dia {r['dia']:.2f} < required {pose['req_dia']:.2f} "
                     f"(at z={r['dia_at'][0]:.1f}, theta={r['dia_at'][1]:.0f})")
            if v["kind"] == "telescoping":
                if dl > P["rattle_max"] + TOL:
                    note.append(f"FAIL rattle {dl:.2f} > {P['rattle_max']}")
                    fail(f"{tag}: length {r['length']:.2f} exceeds req_len+rattle_max "
                         f"({pose['req_len'] + P['rattle_max']:.2f})")
                elif dl >= -TOL:
                    note.append("travel ok")
            print(f"{v['name']:<22}{pose['name'][:25]:<26}{pose['req_len']:>7.2f}{r['length']:>8.2f}{dl:>7.2f}"
                  f"{pose['req_dia']:>7.2f}{r['dia']:>8.2f}{dd:>7.2f}  {'; '.join(note)}")


# ---------------------------------------------------------------- 3 watertight
def all_stls(man):
    return sorted({p["stl"] for v in man["variants"] for p in v["parts"]})


def check_manifold(mp, man):
    import manifold3d
    print("\n=== 3. WATERTIGHT / MANIFOLD ===")
    hdr = (f"{'part':<34}{'faces':>8}{'wt':>4}{'wind':>5}{'vol':>5}{'euler':>6}{'bodies':>7}"
           f"{'degen':>6}{'manifold':>10}{'volume mm3':>12}")
    print(hdr)
    print("-" * len(hdr))
    for stl in all_stls(man):
        m = load_mesh(mp, stl)
        nb = len(m.split(only_watertight=False))
        degen = int((m.area_faces < 1e-8).sum())
        try:
            mf = manifold3d.Manifold(manifold3d.Mesh(np.asarray(m.vertices, np.float32),
                                                     np.asarray(m.faces, np.uint32)))
            st = mf.status()
            st = getattr(st, "name", str(st))
        except Exception as e:  # noqa
            st = "EXC " + str(e)[:20]
        eul = m.euler_number
        print(f"{Path(stl).name[:33]:<34}{len(m.faces):>8}{str(m.is_watertight)[0]:>4}"
              f"{str(m.is_winding_consistent)[0]:>5}{str(m.is_volume)[0]:>5}{eul:>6}{nb:>7}"
              f"{degen:>6}{st:>10}{m.volume:>12.1f}")
        if not m.is_watertight:
            fail(f"{stl}: not watertight")
        if not m.is_winding_consistent:
            fail(f"{stl}: winding inconsistent")
        if not m.is_volume:
            fail(f"{stl}: not a valid volume")
        if eul % 2 != 0 or eul > 2 * nb:
            fail(f"{stl}: euler number {eul} implausible for {nb} bodies")
        if not st.endswith("NoError"):
            fail(f"{stl}: manifold3d status {st}")
        if degen:
            warn(f"{stl}: {degen} degenerate (zero-area) faces")
        if nb > 1:
            warn(f"{stl}: {nb} disconnected bodies")


# ---------------------------------------------------------------- 4 overhang
def check_overhang(mp, man):
    P = man["params"]
    print(f"\n=== 4. OVERHANGS (max {P['max_overhang_deg']} deg from vertical + 1.5 tol; print frame) ===")
    # A face tilted by angle a from vertical has normal_z = -sin(a). (The brief wrote cos, which would
    # flag exact 45-degree faces; sin is the geometrically correct threshold.)
    thr = -math.sin(math.radians(P["max_overhang_deg"] + 1.5))
    for stl in all_stls(man):
        m = load_mesh(mp, stl)
        zf = m.vertices[m.faces][:, :, 2]
        cand = (m.face_normals[:, 2] < thr) & ~(zf < 0.05).all(1)
        lab = cand & (zf <= P["label_depth"] + 0.1).all(1)
        bad = cand & ~lab
        A = m.area_faces
        print(f"{Path(stl).name}: label-bridge area {A[lab].sum():.2f} mm2; "
              f"other overhang area {A[bad].sum():.2f} mm2")
        if not bad.any():
            continue
        idx = np.flatnonzero(bad)
        pos = -np.ones(len(m.faces), int)
        pos[idx] = np.arange(len(idx))
        adj = m.face_adjacency
        sel = bad[adj[:, 0]] & bad[adj[:, 1]]
        a, b = pos[adj[sel, 0]], pos[adj[sel, 1]]
        g = coo_matrix((np.ones(len(a)), (a, b)), shape=(len(idx), len(idx)))
        nc, lbl = connected_components(g, directed=False)
        rows = []
        for c in range(nc):
            f = idx[lbl == c]
            vv = m.vertices[m.faces[f].ravel()]
            rows.append((A[f].sum(), vv.min(0), vv.max(0), len(f)))
        rows.sort(key=lambda r: -r[0])
        for area, lo, hi, nf in rows[:25]:
            s = (f"{stl}: overhang cluster {area:.2f} mm2 ({nf} faces) z {lo[2]:.2f}..{hi[2]:.2f} "
                 f"bbox x[{lo[0]:.1f},{hi[0]:.1f}] y[{lo[1]:.1f},{hi[1]:.1f}]")
            (fail if area > 0.5 else warn)(s)
        if len(rows) > 25:
            warn(f"{stl}: ... and {len(rows) - 25} more smaller clusters")


# ---------------------------------------------------------------- 5 walls
def worst3(rows):
    """rows: (value, z, theta, extra); three smallest values that are spatially distinct."""
    out = []
    for r in sorted(rows, key=lambda r: r[0]):
        if all(abs(r[1] - q[1]) > 2 or abs((r[2] - q[2] + 180) % 360 - 180) > 20 for q in out):
            out.append(r)
        if len(out) == 3:
            break
    return out


def check_walls(mp, man):
    P = man["params"]
    print(f"\n=== 5. WALL / CAP THICKNESS (print frame; need wall>={P['wall']}, cap>={P['end_cap']}) ===")
    # bayonet receivers may be thinner outside the J-slot: a ray whose wall starts more than
    # 1 mm beyond the part's bore is in the groove, and is held to groove_wall instead
    groove = {p["stl"]: p.get("groove_wall") for vv in man["variants"] for p in vv["parts"]}
    tol = P.get("stl_tolerance", 0.04) + 0.01
    for stl in all_stls(man):
        m = load_mesh(mp, stl)
        z0, z1 = m.bounds[0][2], m.bounds[1][2]
        name = Path(stl).name
        if z1 - z0 < 3.0:
            print(f"{name}: too short for wall check")
            continue
        zs = np.arange(z0 + 1.5, z1 - 1.5 + 1e-9, 1.0)
        th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        o, d, Z, TH = rays_radial(zs, th)
        # each ray is cast twice, 0.07 mm apart: a ray that skims a sloped face (a lead-in
        # ramp) at exactly its height picks up a sliver from one mesh triangle; a real thin
        # wall shows in both
        o2 = np.array(o, float) + [0, 0, 0.07]
        rows, rin = [], np.inf
        for i, ((t, sg), (t2, sg2)) in enumerate(zip(cast(m, o, d), cast(m, o2, d))):
            hits = [v[0] for v in (intervals(t, sg), intervals(t2, sg2)) if v and not v[0][2]]
            if len(hits) < 2:
                continue          # no hit, or axis inside material (cap region)
            a, b, _ = max(hits, key=lambda h: h[1] - h[0])
            rows.append((b - a, Z[i], float(np.degrees(TH[i])), a))
            rin = min(rin, a)
        if not rows:
            print(f"{name}: no radial wall found")
        else:
            gw = groove.get(stl)
            sets = [("", P["wall"], [r for r in rows if not gw or r[3] <= rin + 1.0])]
            if gw:
                sets.append(("J-slot ", gw, [r for r in rows if r[3] > rin + 1.0]))
            for what, need, rr in sets:
                if not rr:
                    continue
                w = worst3(rr)
                print(f"{name}: min {what}radial wall {w[0][0]:.3f} mm, need {need} (min inner radius {rin:.2f})")
                for r in w:
                    print(f"      wall {r[0]:.3f} at z={r[1]:.1f} theta={r[2]:.0f} (inner surface r={r[3]:.2f})")
                if w[0][0] < need - tol:
                    fail(f"{stl}: {what}radial wall {w[0][0]:.3f} < {need} at z={w[0][1]:.1f} theta={w[0][2]:.0f}")
        # cap / floor
        o, d = rays_vertical([[0, 0]], z0 - 1.0)
        if not intervals(*cast(m, o, d)[0]):
            print("      (no cap on axis)")
            continue
        rmax = max((rin if np.isfinite(rin) else 0.0) - 2.0, 0.0)
        pts = [(0.0, 0.0, 0.0)]
        if rmax > 0:
            for r in np.linspace(rmax / 12, rmax, 12):
                pts += [(r * math.cos(a), r * math.sin(a), math.degrees(a))
                        for a in np.radians(np.arange(0, 360, 30))]
        # three slightly offset rays per point, median thickness: a ray that grazes the
        # vertical wall of an engraved letter mis-pairs its hits, its neighbours don't
        jit = [(0.0, 0.0), (0.07, 0.03), (-0.04, 0.06)]
        o, d = rays_vertical([[p[0] + jx, p[1] + jy] for p in pts for jx, jy in jit], z0 - 1.0)
        hits = cast(m, o, d)
        caps = []
        for k, (x, y, a) in enumerate(pts):
            th = []
            for t, sg in hits[3 * k:3 * k + 3]:
                v = intervals(t, sg)
                if v:
                    th.append((v[0][1] - v[0][0], v[0][0]))
            if len(th) >= 2:
                th.sort()
                caps.append((th[len(th) // 2][0], math.hypot(x, y), a, th[len(th) // 2][1] + z0 - 1.0))
        if caps:
            caps.sort()
            print(f"      min cap {caps[0][0]:.3f} mm")
            for r in worst3([(q[0], q[3], q[2], q[1]) for q in caps]):
                print(f"      cap {r[0]:.3f} at r={r[3]:.1f} theta={r[2]:.0f} (cap starts z={r[1]:.2f})")
            if caps[0][0] < P["end_cap"] - P.get("stl_tolerance", 0.04) - 0.01:
                fail(f"{stl}: cap {caps[0][0]:.3f} < {P['end_cap']} at r={caps[0][1]:.1f} theta={caps[0][2]:.0f}")


def check_interference(mp, man):
    """Parts must not overlap in any pose (threads interleave, pins sit in their notches)."""
    import manifold3d as m3
    print("\n=== 6. INTERFERENCE (pairwise overlap volume per pose) ===")
    for v in man["variants"]:
        for pose in v["poses"]:
            parts = assemble(mp, v, pose)
            mf = {n: m3.Manifold(mesh=m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                                 tri_verts=np.asarray(m.faces, np.uint32)))
                  for n, m in parts}
            names = list(mf)
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    vol = (mf[names[i]] ^ mf[names[j]]).volume()
                    tag = "ok" if vol < 1.0 else "FAIL"
                    print(f"{v['name']:16s} {pose['name']:24s} {names[i]}/{names[j]}: {vol:8.2f} mm3  {tag}")
                    if vol >= 1.0:
                        fail(f"{v['name']} / {pose['name']}: {names[i]} and {names[j]} overlap {vol:.1f} mm3")


def check_lens_clearance(mp, man):
    """kind=='lens' visuals (already in assembled frame) must not overlap printed parts; foam may touch."""
    import manifold3d as m3
    from scipy.spatial import cKDTree

    def to_m3(m):
        return m3.Manifold(mesh=m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                        tri_verts=np.asarray(m.faces, np.uint32)))
    print("\n=== 7. LENS CLEARANCE (lens visuals vs printed parts, per pose) ===")
    n_checked = 0
    for v in man["variants"]:
        for pose in v["poses"]:
            lenses = [x for x in pose.get("visual", []) if x.get("kind") == "lens"]
            if not lenses:
                continue
            parts = assemble(mp, v, pose)
            pm = {n: to_m3(m) for n, m in parts}
            case = trimesh.util.concatenate([m for _, m in parts])
            tree = cKDTree(np.vstack([case.sample(60000), case.vertices]))
            for lv in lenses:
                lm = trimesh.load(resolve(mp, lv["stl"]), force="mesh", process=True)
                if lm.is_watertight and lm.volume < 0:
                    lm.invert()
                lf = to_m3(lm)
                gap = tree.query(lm.sample(20000))[0].min()
                for pn, pmf in pm.items():
                    vol = (lf ^ pmf).volume()
                    n_checked += 1
                    tag = "ok" if vol < 0.5 else "FAIL"
                    print(f"{v['name']:16s} {pose['name'][:24]:24s} {lv['name']}/{pn}: overlap {vol:8.2f} mm3 {tag}")
                    if vol >= 0.5:
                        fail(f"{v['name']} / {pose['name']}: lens {lv['name']} overlaps {pn} by {vol:.1f} mm3")
                print(f"{'':16s} {'':24s} {lv['name']}: min gap to case (approx, sampled) {gap:.2f} mm")
    if not n_checked:
        warn("no lens visuals in manifest; lens clearance not checked")


def check_print_gap(mp, man):
    """Smallest gap between mating parts in every pose, for print tolerance.

    Surfaces that are meant to touch are flat stops (lid ceiling on the rim, lock ring on
    the rim), so near-horizontal faces (|n_z| > 0.9) are left out; every sliding, threaded
    or bayonet surface is checked. Gaps are measured on the meshes (chord sag included).
    """
    from scipy.spatial import cKDTree
    need = man["params"].get("min_gap", 0.2)
    print(f"\n=== 8. PRINT GAP between mating parts (need >= {need} mm; flat stops excluded) ===")
    for v in man["variants"]:
        for pose in v["poses"]:
            parts = dict(assemble(mp, v, pose))
            names = list(parts)
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    if sorted([names[i], names[j]]) in [sorted(p) for p in v.get("stop_pairs", [])]:
                        print(f"{v['name']:16s} {pose['name']:24s} {names[i]}/{names[j]}: seats on, doesn't slide - skipped")
                        continue
                    a, b = parts[names[i]], parts[names[j]]
                    gaps = []
                    for src, dst in ((a, b), (b, a)):
                        keep = np.abs(src.face_normals[:, 2]) < 0.9
                        pts = src.triangles_center[keep]
                        pts = np.vstack([pts, src.vertices])
                        near = cKDTree(dst.vertices).query(pts, distance_upper_bound=3.0)[0] < 3.0
                        if near.any():
                            _, dist, tri = trimesh.proximity.closest_point(dst, pts[near])
                            # skip points whose nearest surface is a flat stop on the other part
                            ok = np.abs(dst.face_normals[tri, 2]) < 0.9
                            if ok.any():
                                gaps.append(dist[ok].min())
                    if not gaps:
                        continue
                    g = min(gaps)
                    tag = "ok" if g >= need else "FAIL"
                    print(f"{v['name']:16s} {pose['name']:24s} {names[i]}/{names[j]}: min gap {g:5.2f} mm  {tag}")
                    if g < need:
                        fail(f"{v['name']} / {pose['name']}: {names[i]}-{names[j]} gap {g:.2f} mm < {need}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/manifest.json")
    mp = Path(ap.parse_args().manifest).resolve()
    man = json.loads(mp.read_text())
    t0 = time.time()
    for name, fn in (("fit", check_fit), ("manifold", check_manifold),
                     ("overhang", check_overhang), ("walls", check_walls),
                     ("interference", check_interference),
                     ("lens", check_lens_clearance), ("gap", check_print_gap)):
        t = time.time()
        fn(mp, man)
        print(f"  [{name}: {time.time() - t:.1f}s]")
    print(f"\n{len(warns)} warning(s), {len(fails)} FAIL(s), total {time.time() - t0:.1f}s")
    if fails:
        print("\nFAILURES:")
        for f in fails:
            print(" - " + f)
        print("\nRESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
