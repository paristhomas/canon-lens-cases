"""Write out/report.md: measured fit table, envelopes, parts, volume and print-time estimates.

Print time is a slicer-free estimate: these parts are thin-walled, so with 6 perimeters they
print essentially solid; time = volume / average volumetric rate x 1.15 (travel, layer
changes). Rates: 5 mm3/s (PETG on a typical bedslinger, e.g. Prusa MK3/MK4) and
12 mm3/s (fast CoreXY, e.g. Bambu X1/P1). Treat as +/-30 %.
"""
import json
from pathlib import Path

import verify as V

PETG_DENSITY = 1.27   # g/cm3 (ASA ~1.07)
RATES = (5.0, 12.0)   # mm3/s
OVERHEAD = 1.15


def hm(sec):
    h, m = divmod(round(sec / 60), 60)
    return f"{h}h{m:02d}"


def main():
    mp = Path("out/manifest.json").resolve()
    man = json.loads(mp.read_text())
    L = ["# Generated report", "", "Produced by `python report.py` from `out/manifest.json`; "
         "fit values are measured on the exported meshes.", ""]

    L += ["## Fit table", "",
          "| Variant | Configuration | Required L x Ø | Measured interior L x Ø | Length margin | Ø margin |",
          "|---|---|---|---|---|---|"]
    for v in man["variants"]:
        for p in v["poses"]:
            r = V.measure_fit(V.assemble(mp, v, p))
            L.append(f"| {v['name']} | {p['name']} | {p['req_len']:.1f} x {p['req_dia']:.1f} | "
                     f"{r['length']:.2f} x {r['dia']:.2f} | {r['length'] - p['req_len']:+.2f} | "
                     f"{r['dia'] - p['req_dia']:+.2f} |")

    L += ["", "## External envelope", "",
          "| Variant | Max outer Ø (nothing protrudes) | Length | Extended | Lanyard lug |",
          "|---|---|---|---|---|"]
    for v in man["variants"]:
        e = v["envelope"]
        ext = f"{e['length_ext']:.1f}" if e["length_ext"] else "-"
        lug = f"+{e['lug_projection']:.0f} mm one side" if e["lug_projection"] else "off"
        L.append(f"| {v['name']} | {e['od']:.1f} | {e['length']:.1f} | {ext} | {lug} |")

    L += ["", "## Parts, material and print time", "",
          f"| Variant | Parts | Volume cm3 | PETG g | Time @{RATES[0]:.0f} mm3/s | Time @{RATES[1]:.0f} mm3/s |",
          "|---|---|---|---|---|---|"]
    summary = {}
    for v in man["variants"]:
        vol = sum(p["volume_mm3"] for p in v["parts"])
        t = [vol / r * OVERHEAD for r in RATES]
        summary[v["name"]] = (len(v["parts"]), vol, t)
        names = ", ".join(p["name"] for p in v["parts"])
        L.append(f"| {v['name']} | {len(v['parts'])} ({names}) | {vol / 1000:.1f} | "
                 f"{vol / 1000 * PETG_DENSITY:.0f} | {hm(t[0])} | {hm(t[1])} |")

    L += ["", "### Per part", "", "| STL | Volume cm3 | PETG g |", "|---|---|---|"]
    for v in man["variants"]:
        for p in v["parts"]:
            L.append(f"| `{Path(p['stl']).name}` | {p['volume_mm3'] / 1000:.1f} | "
                     f"{p['volume_mm3'] / 1000 * PETG_DENSITY:.0f} |")

    out = Path("out/report.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
