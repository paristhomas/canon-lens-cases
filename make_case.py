"""Fixed-length case for any lens (the generic version of cases 2 and 3).

    python make_case.py --name sigma30 --dia 65 --length 50.5 --rear-cap 12 --label "SIGMA 30 1.4"
    python make_case.py --name ef35 --dia 77.9 --length 62.6 --style threaded

--dia / --length are the lens's max diameter and mount-to-front length without caps;
the front cap, foam and clearances come from params.py. Writes out/<name>_<style>_{body,lid}.{stl,step}.
"""
import argparse
from pathlib import Path

from build123d import export_step, export_stl

import params as P
from cases import STYLES, TELE_ONLY, fixed_case
STYLES = tuple(s for s in STYLES if s not in TELE_ONLY)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--dia", type=float, required=True, help="lens max diameter, mm")
    ap.add_argument("--length", type=float, required=True, help="lens length without caps, mm")
    ap.add_argument("--rear-cap", type=float, default=P.EF_REAR_CAP, help="rear cap protrusion, mm")
    ap.add_argument("--label", default=None, help="engraved text; use '|' for a new line")
    ap.add_argument("--style", choices=STYLES + ("both",), default="both")
    a = ap.parse_args()
    lens = P.Item(a.name, a.dia, a.length, (a.label or a.name).split("|")[0])
    cfg = P.Config(a.name, (lens,), a.rear_cap)
    lines = a.label.split("|") if a.label else None
    out = Path("out"); out.mkdir(exist_ok=True)
    for style in (STYLES if a.style == "both" else (a.style,)):
        v = fixed_case(a.name, cfg, style, lines)
        for pname, (solid, to_print) in v.parts.items():
            stem = out / f"{v.name}_{pname}"
            printed = to_print.loc() * solid
            export_step(printed, f"{stem}.step")
            export_stl(printed, f"{stem}.stl", tolerance=0.05, angular_tolerance=0.2)
        d = v.dims
        req = v.poses[0]
        print(f"{v.name}: required {req['req_dia']:.1f} x {req['req_len']:.1f} inside, "
              f"bore {d['bore']:.1f}, outer {d['od']:.1f} x {d['length']:.1f} mm -> {out}/{v.name}_*")


if __name__ == "__main__":
    main()
