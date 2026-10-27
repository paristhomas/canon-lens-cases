"""Non-printed visual contents: foam padding and lens proxy models.

No CAD is published for these lenses, so each lens is a stepped solid of revolution that
fills its spec envelope (max diameter x length): if the proxy clears the case, the real
lens does. Caps and the adapter are simple discs/cylinders from the params estimates.
"""
from build123d import Align, Cylinder, Pos

import params as P
from .prims import revolve_rz


def _cyl(d, h, z):
    return Pos(0, 0, z) * Cylinder(d / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _lens(item, z):
    """Mount-down lens: narrower mount section, full barrel, short taper to the front."""
    r, L = item.dia / 2, item.length
    rm = min(r, 31.0)                    # mount flange region
    rf = max(item.front_dia / 2, rm)
    return revolve_rz([(0, z), (rm, z), (rm, z + 5), (r, z + 7), (r, z + L - 6),
                       (rf + 1, z + L), (0, z + L)])


def contents(cfg, bore, z_floor, z_ceil, foam=True, gap=P.BARE_GAP):
    """[(name, kind, solid)] for one configuration inside a case interior. Without foam the
    lens stands `gap` off the floor."""
    if foam:
        fb, ft, fr = P.FOAM_END_BOTTOM, P.FOAM_END_TOP - cfg.foam_less, P.FOAM_RADIAL
        out = [("foam_end_bottom", "foam", _cyl(bore - 0.2, fb, z_floor)),
               ("foam_end_top", "foam", _cyl(bore - 0.2, ft, z_ceil - ft)),
               ("foam_sleeve", "foam", _cyl(bore - 0.2, z_ceil - z_floor - fb - ft, z_floor + fb)
                - _cyl(min(bore - 2 * fr, cfg.dia + P.FIT_CLEAR_DIA), z_ceil - z_floor, z_floor))]
    else:
        fb, out = gap, []
    z = z_floor + fb
    if not cfg.items:     # generic position: one cylinder for "any lens + caps this long"
        out.append(("lens_generic", "lens", _cyl(cfg.dia, cfg.stack, z)))
        return out
    rear_d = P.RF_REAR_CAP_DIA if cfg.rear_cap == P.RF_REAR_CAP else P.EF_REAR_CAP_DIA
    out.append(("rear_cap", "lens", _cyl(rear_d, cfg.rear_cap, z)))
    z += cfg.rear_cap
    # items are listed lens first; physically the adapter sits on the mount (below the lens)
    for item in sorted(cfg.items, key=lambda i: i is not P.A1):
        if item is P.A1:
            out.append(("adapter", "lens", _cyl(item.dia, item.length, z)))
        else:
            out.append((f"lens_{item.short.replace(' ', '').replace('/', '')}", "lens", _lens(item, z)))
            front = item
        z += item.length
    out.append(("front_cap", "lens", _cyl(front.front_dia, cfg.front_cap, z)))
    return out
