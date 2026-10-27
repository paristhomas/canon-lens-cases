"""Build every variant, export STEP + STL (print orientation) to out/, write out/manifest.json.

    python build_all.py              # all 6 variants
    python build_all.py case2        # one case (both styles)
    python build_all.py case1_threaded
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from build123d import export_step, export_stl

import params as P
from cases import STYLES, all_variants

OUT = Path("out")
STL_TOL = 0.008  # mm chord sag on curved surfaces: ~1.8 mm facets on a 97 mm case


def main(only=None):
    OUT.mkdir(exist_ok=True)
    man_path = OUT / "manifest.json"
    manifest = json.loads(man_path.read_text()) if (only and man_path.exists()) else {"variants": []}
    manifest["params"] = dict(wall=P.WALL, end_cap=P.END_CAP, max_overhang_deg=P.MAX_OVERHANG_DEG,
                              rattle_max=P.RATTLE_MAX, label_depth=P.LABEL_DEPTH,
                              stl_tolerance=STL_TOL, min_gap=P.MIN_PRINT_GAP)
    done = {v["name"]: v for v in manifest["variants"]}
    for v in all_variants(only):
        t0 = time.time()
        parts = []
        for pname, (solid, to_print) in v.parts.items():
            printed = to_print.loc() * solid
            stem = OUT / f"{v.name}_{pname}"
            export_step(printed, f"{stem}.step")
            # the small lock ring gets a finer mesh: coarse facets where its thread is trimmed
            # at the faces tilt past 45 deg and trip the overhang check
            tol, ang = (STL_TOL / 2, 0.03) if pname == "ring" else (STL_TOL, 0.05)
            export_stl(printed, f"{stem}.stl", tolerance=tol, angular_tolerance=ang)
            parts.append(dict(name=pname, stl=f"{stem.as_posix()}.stl", step=f"{stem.as_posix()}.step",
                              to_use=np.linalg.inv(to_print.matrix()).flatten().tolist(),
                              volume_mm3=round(solid.volume, 1), valid=bool(solid.is_valid),
                              groove_wall=v.groove_walls.get(pname)))
        vis_dir = OUT / "visual"
        vis_dir.mkdir(exist_ok=True)
        for k, p in enumerate(v.poses, 1):
            p["visual_out"] = []
            for vname, kind, solid in p.get("visual", []):
                f = vis_dir / f"{v.name}_p{k}_{vname}.stl"
                export_stl(solid, str(f), tolerance=0.05, angular_tolerance=0.1)
                p["visual_out"].append(dict(name=vname, kind=kind, stl=f.as_posix()))
        d = v.dims
        done[v.name] = dict(
            name=v.name, case=v.case, style=v.style, kind=v.kind, title=v.title,
            envelope=dict(od=round(d["od"], 2), od_features=round(d["od_features"], 2),
                          length=round(d["length"], 2),
                          length_ext=None if d["length_ext"] is None else round(d["length_ext"], 2),
                          lug_projection=d["lug"]),
            design=dict(bore=d["bore"], overlap_min=d.get("overlap_min")),
            parts=parts,
            poses=[dict(name=p["name"], req_len=round(p["req_len"], 2),
                        req_dia=round(p["req_dia"], 2), target_len=p["target"],
                        transforms={k: x.matrix().flatten().tolist() for k, x in p["transforms"].items()},
                        visual=p["visual_out"])
                   for p in v.poses],
            explode={k: x.matrix().flatten().tolist() for k, x in v.explode.items()},
            stop_pairs=v.stop_pairs,
        )
        print(f"{v.name:18s} {len(parts)} parts  OD {d['od']:.1f}  L {d['length']:.1f}"
              + (f" -> {d['length_ext']:.1f}" if d["length_ext"] else "")
              + f"   valid={[p['valid'] for p in parts]}  {time.time() - t0:.0f}s", flush=True)
    order = [f"{c}_{s}" for c in ("case1", "case2", "case3", "case4", "case5", "case6") for s in STYLES]
    manifest["variants"] = sorted(done.values(), key=lambda x: order.index(x["name"]) if x["name"] in order else 99)
    man_path.write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
