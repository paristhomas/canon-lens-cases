"""Build fake STLs + manifest for testing verify.py / render.py.

usage: python tests/make_fake_manifest.py [--out out_fake] [--clean]
Default includes planted faults (30-deg-above-horizontal flange, 2.0 mm thin wall, rattle fault).
--clean omits all faults.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def revolve(profile, sections=96):
    m = trimesh.creation.revolve(np.array(profile, float), sections=sections)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    if m.is_watertight and m.volume < 0:
        m.invert()
    return m


def flip_z(zoff):
    M = np.eye(4)
    M[2, 2] = -1
    M[2, 3] = zoff
    return M


def trans(z):
    M = np.eye(4)
    M[2, 3] = z
    return M


def cup(ro, ri, h, floor, extra=None):
    """Cup profile; floor at z=0..floor. extra: replace outer wall list of (r,z) points."""
    outer = extra or [(ro, 0), (ro, h)]
    return [(0, 0)] + outer + [(ri, h), (ri, floor), (0, floor)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out_fake")
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    faults = not a.clean
    params = dict(wall=2.4, end_cap=3.0, max_overhang_deg=45.0, rattle_max=3.0, label_depth=0.6)

    def save(name, mesh):
        p = out / f"{name}.stl"
        mesh.export(p)
        return str(p).replace("\\", "/")

    variants = []
    # ---- fixed case: body (r_out 20, r_in 17.6, h 50, floor 3) + lid (cap top, wall down)
    if faults:   # thin 2.0 wall section z 20..25
        outer = [(20, 0), (20, 20), (19.6, 20), (19.6, 25), (20, 25), (20, 50)]
    else:
        outer = [(20, 0), (20, 50)]
    body = revolve(cup(20, 17.6, 50, 3, outer))
    if faults:   # flange whose underside is 30 deg above horizontal (60 deg from vertical)
        lid_prof = [(0, 0), (22.6, 0), (22.6, 7), (25, 8.39), (25, 10), (22.6, 10), (22.6, 12),
                    (20.2, 12), (20.2, 3), (0, 3)]
    else:
        lid_prof = [(0, 0), (22.6, 0), (22.6, 12), (20.2, 12), (20.2, 3), (0, 3)]
    lid = revolve(lid_prof)
    variants.append(dict(
        name="fake_fixed", case="fake", style="thread", kind="fixed", title="Fake fixed case",
        envelope=dict(od=50, od_features=50, length=53, length_ext=None),
        parts=[dict(name="body", stl=save("fake_fixed_body", body), step="", to_use=list(np.eye(4).ravel())),
               dict(name="lid", stl=save("fake_fixed_lid", lid), step="", to_use=list(flip_z(53.0).ravel()))],
        poses=[dict(name="closed", req_len=46.0, req_dia=35.0, target_len=47.0, transforms={})],
        explode=dict(lid=list(trans(30).ravel()))))

    # ---- telescoping: body cup + inner sleeve (cap at top when in use)
    tb = revolve(cup(20, 17.6, 40, 3))
    inner = revolve([(0, 0), (17.4, 0), (17.4, 40), (15, 40), (15, 3), (0, 3)])
    # inner in use: flipped, cap underside at z=U  -> flip_z(U + 3)  (cap occupies U..U+3)
    def pose(name, rl, U):
        return dict(name=name, req_len=rl, req_dia=28.0, target_len=rl + 1.0,
                    transforms=dict(inner=list(trans(U - 27.0).ravel())))
    # base to_use puts cap underside at z=27 (flip_z(30)); pose shifts to U
    def tele(name, poses):
        return dict(
            name=name, case="fake", style="bayonet", kind="telescoping", title="Fake telescoping " + name,
            envelope=dict(od=40, od_features=40, length=43, length_ext=80),
            parts=[dict(name="body", stl=save("fake_tele_body", tb), step="", to_use=list(np.eye(4).ravel())),
                   dict(name="inner", stl=save("fake_tele_inner", inner), step="", to_use=list(flip_z(30.0).ravel()))],
            poses=poses, explode=dict(inner=list(trans(40).ravel())))
    variants.append(tele("fake_tele", [pose("1: short", 30.0, 3 + 31.0), pose("2: long", 60.0, 3 + 61.0)]))
    if faults:
        variants.append(tele("fake_tele_bad", [pose("1: too loose", 25.0, 3 + 31.0),
                                               pose("2: too short", 62.0, 3 + 61.0)]))

    man = dict(params=params, variants=variants)
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    print("wrote", out / "manifest.json")


if __name__ == "__main__":
    main()
