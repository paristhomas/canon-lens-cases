"""Decimated meshes + manifest for the web viewer -> out/web/ (run after build_all.py, report.py).

Full-resolution STLs are 5-16 MB each; the viewer only needs enough triangles to read the
shapes, so parts are decimated to ~MAX_FACES and visuals to ~VIS_FACES.
"""
import base64
import json
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh

import verify as V

MAX_FACES = 60000
VIS_FACES = 4000
OUT = Path("out/web")


def decimate(mesh, target):
    if len(mesh.faces) <= target:
        return mesh
    v, f = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                                        target_reduction=1 - target / len(mesh.faces))
    return trimesh.Trimesh(v, f, process=False)


def save(mesh, stl_name):
    """Binary STL wrapped as base64 JSON (the artifact host serves .json, not .stl)."""
    fn = f"m/{Path(stl_name).stem}.json"
    data = trimesh.exchange.stl.export_stl(mesh)
    (OUT / fn).write_text(json.dumps({"stl_b64": base64.b64encode(data).decode()}))
    return fn


def main():
    mp = Path("out/manifest.json").resolve()
    man = json.loads(mp.read_text())
    (OUT / "m").mkdir(parents=True, exist_ok=True)
    web = {"params": man["params"], "variants": []}
    for v in man["variants"]:
        wv = {k: v[k] for k in ("name", "case", "style", "kind", "title", "envelope", "design", "explode")}
        wv["parts"] = []
        for p in v["parts"]:
            fn = save(decimate(trimesh.load(p["stl"]), MAX_FACES), p["stl"])
            wv["parts"].append(dict(name=p["name"], stl=fn, to_use=p["to_use"],
                                    volume_cm3=round(p["volume_mm3"] / 1000, 1)))
        wv["poses"] = []
        for p in v["poses"]:
            fit = V.measure_fit(V.assemble(mp, v, p))
            vis = []
            for q in p.get("visual", []):
                fn = save(decimate(trimesh.load(q["stl"]), VIS_FACES), q["stl"])
                vis.append(dict(name=q["name"], kind=q["kind"], stl=fn))
            wv["poses"].append(dict(name=p["name"], req_len=p["req_len"], req_dia=p["req_dia"],
                                    meas_len=round(fit["length"], 2), meas_dia=round(fit["dia"], 2),
                                    transforms=p["transforms"], visual=vis))
        web["variants"].append(wv)
        print(v["name"], "ok")
    (OUT / "models.json").write_text(json.dumps(web))
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"{total / 1e6:.1f} MB in {OUT}")


if __name__ == "__main__":
    main()
