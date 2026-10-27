"""J-slot bayonet: self-supporting pins, matching groove (entry channel + twist leg + hook
notch) and a detent bump in each leg.

Geometry is in the assembled, *seated* pose: pins sit in the notch at angle 0; the leg runs
from the notch to the entry channel at +twist. The leg is offset axially from the notch by
`notch` toward the direction the pin travels on insertion (`insert_dir` = -1 if the pinned
part moves down into the slotted part, +1 if up). Foam preload pushes the pin back into the
notch, so the joint is locked axially and rotationally.

chamfer: which pin face is 45 deg ("bottom" or "top", in use orientation) - choose the one
that faces down when the pinned part is printed.
"""
import math

from build123d import Cylinder, Align, Plane, Polygon, Pos, Rot, extrude, loft

from .prims import revolve_rz


def pin_profile(r_wall, zb, zt, proj, chamfer):
    e = 0.3
    if chamfer == "bottom":
        return [(r_wall - e, zb - e), (r_wall + proj, zb + proj), (r_wall + proj, zt), (r_wall - e, zt)]
    return [(r_wall - e, zb), (r_wall + proj, zb), (r_wall + proj, zt - proj), (r_wall - e, zt + e)]


def groove_profile(r_pin_wall, r_cut, depth, zb, zt, chamfer, c):
    """Slot cross-section: pin profile grown by clearance c, cut from r_cut outward."""
    r0, r1 = r_cut - 0.3, r_cut + depth
    if chamfer == "bottom":
        lo = lambda r: zb - c + (r - r_pin_wall)
        return [(r0, lo(r0)), (r1, lo(r1)), (r1, zt + c), (r0, zt + c)]
    hi = lambda r: zt + c - (r - r_pin_wall)
    return [(r0, zb - c), (r1, zb - c), (r1, hi(r1)), (r0, hi(r0))]


def pins(r_wall, zb, zt, proj, chamfer, n, width):
    half = math.degrees(width / 2 / r_wall)
    one = revolve_rz(pin_profile(r_wall, zb, zt, proj, chamfer), -half, half)
    return [Rot(0, 0, i * 360 / n) * one for i in range(n)]


def j_slot(r_pin_wall, r_cut, depth, zb, zt, chamfer, c, n, width, twist, notch, insert_dir,
           channel_to, bump_h, bump_r):
    """Return (void_solids, bump_solids) for one lock position, repeated n times.

    channel_to: z the entry channel runs to (the open rim of the slotted part), or None
    if this position's leg joins a channel cut separately (telescoping track).
    """
    half = math.degrees((width / 2 + c) / r_pin_wall)
    off = insert_dir * notch
    notch_v = revolve_rz(groove_profile(r_pin_wall, r_cut, depth, zb, zt, chamfer, c), -half, half)
    leg_prof = groove_profile(r_pin_wall, r_cut, depth, zb + off, zt + off, chamfer, c)
    leg_v = revolve_rz(leg_prof, -half, twist + half)
    voids = [notch_v, leg_v]
    if channel_to is not None:
        if channel_to < zb:   # slotted part's rim is below: channel rises to the leg top
            end = max(zt, zt + off) + c
        else:                 # rim above: channel drops to the leg bottom
            end = min(zb, zb + off) - c
        voids.append(channel(r_cut, depth, end, channel_to, twist, half))
    # detent bump on the groove floor, just past the notch, trimmed to the leg void
    r_floor = r_cut + depth
    beta = math.degrees(bump_r / r_floor)
    a_b = math.degrees(width / 2 / r_pin_wall) + beta + 0.8
    cyl = Rot(0, 0, a_b) * Pos(r_floor + bump_r - bump_h, 0, 0) * Cylinder(
        bump_r, 400, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    # clip region reaches 0.5 into the wall so the bump fuses volumetrically, not on a
    # coincident cylindrical face (which leaves open edges in the mesh)
    clip = groove_profile(r_pin_wall, r_cut, depth + 0.5, zb + off, zt + off, chamfer, c)
    bump = cyl & revolve_rz(clip, half, twist - half)
    rep = lambda s: [Rot(0, 0, i * 360 / n) * s for i in range(n)]
    return sum((rep(v) for v in voids), []), rep(bump)


def channel(r_cut, depth, z0, z1, angle, half):
    lo, hi = min(z0, z1), max(z0, z1)
    prof = [(r_cut - 0.3, lo), (r_cut + depth, lo), (r_cut + depth, hi), (r_cut - 0.3, hi)]
    return revolve_rz(prof, angle - half, angle + half)


def lead_in(r_cut, depth, angle, half, z_mouth, len_ccw, len_cw, slope, into, seg=6):
    """Lead-in ramps either side of an entry channel at `angle` (deg, half-width `half` deg
    at r_cut).

    Each side is a helical ramp from the rim down to the channel edge, `len_ccw` / `len_cw`
    mm of arc long (counter-clockwise / clockwise side seen from above) at `slope` deg from
    horizontal, so it drops len * tan(slope) at the channel. Ramps of neighbouring channels
    that meet at the rim leave a sharp crest: a pin set down there slides into a channel.
    `into` is +1 if the channel runs up from the mouth, -1 if down. The ramps face the open
    rim, so they print with the rim up. Built from `seg` planar facets per side.
    """
    u = math.radians(half) * r_cut
    rr = r_cut + depth
    k = math.tan(math.radians(slope))
    far = z_mouth - into * 2.0                       # overcut past the rim
    out = []
    for side, length in ((1, len_ccw), (-1, len_cw)):
        if length <= 0:
            continue
        drop = length * k
        ramp = lambda a: z_mouth + into * (drop - min(max(a, 0.0), length) * k)
        z_lo, z_hi = sorted((z_mouth + into * (drop + 1), far))
        edges = [length * j / seg for j in range(seg + 1)]   # arc past the channel edge
        for a0, a1 in zip(edges[:-1], edges[1:]):
            t0, t1 = u + a0 - (0.3 if a0 == 0 else 0), u + a1     # arc from the channel centre
            am, w = (t0 + t1) / 2, (t1 - t0) / 2 + 0.3
            # local x is arc from the facet's middle (CCW); the ramp is linear across it.
            # The facet is lofted toward the axis, so the ramp height is constant along every
            # radial line (a true helical ramp, no sliver between groove floor and bore)
            r_o, r_i = rr + 2, r_cut - 1
            faces = []
            for x in (r_o, r_i):
                s = x / r_cut
                pts = [(-w * s, ramp(am - side * w - u)), (w * s, ramp(am + side * w - u)),
                       (w * s, far), (-w * s, far)]
                faces.append(Plane(origin=(x, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
                             * Polygon(*pts, align=None))
            prism = Rot(0, 0, side * math.degrees(am / r_cut)) * loft(faces, ruled=True)
            d0, d1 = sorted((side * math.degrees(t0 / r_cut), side * math.degrees(t1 / r_cut)))
            ring = revolve_rz([(r_cut - 0.3, z_lo), (rr, z_lo), (rr, z_hi), (r_cut - 0.3, z_hi)], d0, d1)
            out.append(prism & ring)
    res = out[0]
    for s in out[1:]:
        res = res + s
    return Rot(0, 0, angle) * res
