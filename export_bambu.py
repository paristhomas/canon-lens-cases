"""Bambu Studio project files: one 3MF per variant (all its parts on one plate) -> print/bambu/.

Uses the Bambu Studio command line and its installed system profiles: X1 Carbon 0.4 nozzle
(same 256 mm bed as P1S / P1P / X1; Bambu Studio offers to switch printer when the project
is opened for another one), Generic PETG (Generic TPU for the tpu style), 0.20mm Standard with
the overrides below.

usage: python export_bambu.py [variant ...]
env:   BAMBU_STUDIO  path to bambu-studio(.exe)
       BAMBU_PROFILES  the profile folder holding machine/ process/ filament/
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

STUDIO = os.environ.get("BAMBU_STUDIO", r"C:\Program Files\Bambu Studio\bambu-studio.exe")
PROFILES = Path(os.environ.get("BAMBU_PROFILES",
                               Path(os.environ.get("APPDATA", "")) / "BambuStudio" / "system" / "BBL"))
MACHINE, PROCESS, FILAMENT = "Bambu Lab X1 Carbon 0.4 nozzle", "0.20mm Standard @BBL X1C", "Generic PETG"
# README "Printing": solid 2 mm walls (0.42 + 4 x 0.45), 5 / 5 shells,
# sparse gyroid, no supports or brim
OVERRIDES = dict(wall_loops="5", top_shell_layers="5", bottom_shell_layers="5",
                 sparse_infill_density="15%", sparse_infill_pattern="gyroid",
                 enable_support="0", brim_type="no_brim", seam_position="aligned")
# tpu style: 4 mm walls (0.42 + 8 x 0.45)
STYLE = {s: ("Generic TPU", dict(OVERRIDES, wall_loops="9")) for s in ("tpu", "tpu_bayonet")}
OUT = Path("print/bambu")
THICK = ("case1", "case3", "case5")   # params.THICK_WALL_CASES


def profile(kind, name):
    """System profile with its `inherits` chain resolved (the CLI needs complete profiles)."""
    d = json.loads((PROFILES / kind / f"{name}.json").read_text(encoding="utf-8"))
    if d.get("inherits"):
        base = profile(kind, d.pop("inherits"))
        base.update(d)
        d = base
    d.pop("inherits", None)
    d["from"] = "system"
    return d


def main(only=None):
    man = json.loads(Path("out/manifest.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        def write(kind, name, extra, tag):
            d = profile(kind, name)
            d.update(extra)
            p = Path(tmp) / f"{kind}_{tag}.json"
            p.write_text(json.dumps(d, indent=1), encoding="utf-8")
            return p
        for v in man["variants"]:
            if only and v["name"] not in only:
                continue
            fil, over = STYLE.get(v["style"], (FILAMENT, OVERRIDES))
            if not v["style"].startswith("tpu") and v["case"] in THICK:       # 3 mm walls (0.42 + 6 x 0.45)
                over = dict(over, wall_loops="7")
            cfg = {"machine": write("machine", MACHINE, {}, v["style"]),
                   "process": write("process", PROCESS, over, v["style"]),
                   "filament": write("filament", fil, {}, v["style"])}
            stls = [str((Path("print/stl") / Path(p["stl"]).name).resolve()) for p in v["parts"]]
            dst = (OUT / f"{v['name']}.3mf").resolve()
            cmd = [STUDIO, "--arrange", "1", "--orient", "0",
                   "--load-settings", f"{cfg['machine']};{cfg['process']}",
                   "--load-filaments", str(cfg["filament"]), "--export-3mf", str(dst), *stls]
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp)   # it writes result.json there
            ok = r.returncode == 0 and dst.exists()
            print(f"{v['name']:16s} {'ok' if ok else f'FAILED (exit {r.returncode})'}  {dst}", flush=True)
            if not ok:
                sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
