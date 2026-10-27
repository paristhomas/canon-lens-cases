"""Grip flutes, concave anti-roll cuts, lock arrow, entry mark, lanyard lug, webbing slot, engraved labels,
desiccant pocket."""
import math

from build123d import (Align, BuildSketch, Circle, Cylinder, FontStyle, Locations, Mode, Plane, Polygon,
                       Pos, Rectangle, RectangleRounded, Rot, Text, extrude)

from .prims import extrude_xz, revolve_rz


def _ang_dist(a, b):
    return abs((a - b + 180) % 360 - 180)


def grip_flutes(r, z0, z1, n, depth, width, skip=(), phase=0.0):
    """Cutting tool for recessed vertical flutes in a cylinder of radius r.

    Scallops of radius width/2, `depth` deep, straight from z0 to z1 (pass a range past the
    part's ends and they run out through them). Flutes sit at phase + k * 360 / n; those
    within 1 deg of an angle in `skip` are left out. Subtract the result from the part.
    """
    rc = width / 2
    with BuildSketch() as sk:
        for i in range(n):
            if any(_ang_dist(phase + i * 360 / n, s) < 1.0 for s in skip):
                continue
            a = math.radians(phase + i * 360 / n)
            d = r + rc - depth
            with Locations((d * math.cos(a), d * math.sin(a))):
                Circle(rc)
    return Pos(0, 0, z0) * extrude(sk.sketch, amount=z1 - z0)


def arc_cuts(r, angles, chord, depth, z_end=None):
    """Cutting tools for slightly concave vertical cuts in a cylinder of radius r.

    Each cut is `chord` wide at the surface and `depth` deep at its centre, scooped by a
    large cylinder, so it reads as a shallow concave arc rather than a flat. The case
    rests on the two edges of a cut instead of rolling. With z_end the cuts stop there,
    running out at 45 deg so the end prints without support; otherwise they run the full
    height of the part.
    """
    a = math.asin(chord / 2 / r)
    d = r - depth
    assert r * (1 - math.cos(a)) < depth, "cut would be convex: narrower chord or deeper cut"
    cx = (d * d - r * r) / (2 * (d - r * math.cos(a)))     # cutter centre on the x axis
    one = Pos(cx, 0, 0) * Cylinder(cx - d, 4000)
    if z_end is not None:
        one = one & revolve_rz([(d - 0.1, -10), (r + 5, -10), (r + 5, z_end + depth + 5.2),
                                (d - 0.1, z_end - 0.1)])
    return [Rot(0, 0, ang) * one for ang in angles]


def _padlock(open_, s=1.7):
    """Padlock outline (sketch, body centred on the origin, shackle up). The open one has
    its shackle lifted well clear and swung right, so its free leg hangs outside the body."""
    bw, bh, ro, ri = 5.6 * s, 4.4 * s, 2.0 * s, 1.15 * s
    xl = (ro + ri) / 2                                   # leg centre from the arc centre
    lw = ro - ri                                         # leg width
    dx, yc = (xl, bh / 2 + 2.8 * s) if open_ else (0.0, bh / 2 + 0.9 * s)   # arc centre
    with BuildSketch() as sk:
        RectangleRounded(bw, bh, 0.8 * s)
        with Locations((dx, yc)):
            Circle(ro)
            Circle(ri, mode=Mode.SUBTRACT)
            Rectangle(2 * ro + 1, ro + 1, align=(Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        with Locations((dx - xl, (bh / 2 + yc) / 2)):     # left leg, into the body
            Rectangle(lw, yc - bh / 2 + 0.1)
        if open_:          # right leg: a short stub outside the body, well above it
            with Locations((dx + xl, yc - 0.6 * s)):
                Rectangle(lw, 1.2 * s + 0.1)
        else:
            with Locations((dx + xl, (bh / 2 + yc) / 2)):
                Rectangle(lw, yc - bh / 2 + 0.1)
    return sk.sketch


def lock_arrow(z, r_edge, depth, a_lock=45.0, a_open=135.0):
    """Engraving tools for the top face at height z (read from above): a clockwise arrow
    around the rim from an open padlock (a_open) to a closed one (a_lock), in degrees.
    Every stroke is >= 1.4 mm wide so it survives a 0.6 mm nozzle on the bed face."""
    r_a = r_edge - 13.0                                 # arrow radius (padlocks clear the rim)
    cut = lambda sk: Pos(0, 0, z + 0.01) * extrude(sk, amount=depth + 0.01, dir=(0, 0, -1))
    place = lambda ang, rr: Rot(0, 0, ang - 90) * Pos(0, rr, 0)
    # padlocks stand upright (as read from the front), centred on the arc's ends
    upright = lambda ang: Pos(r_a * math.cos(math.radians(ang)), r_a * math.sin(math.radians(ang)) - 2.0, 0)
    head = math.degrees(6.0 / r_a)
    gap = math.degrees(9.5 / r_a)
    a0, a1 = a_lock + gap + head, a_open - gap           # arc runs a1 -> a0 (clockwise)
    arc = revolve_rz([(r_a - 1.3, z - depth), (r_a + 1.3, z - depth), (r_a + 1.3, z + 0.01),
                      (r_a - 1.3, z + 0.01)], a0, a1)
    with BuildSketch() as tip:      # local +x is the clockwise tangent, +y radially outward
        Polygon((-0.3, -3.4), (6.0, 0), (-0.3, 3.4), align=None)
    return [arc, place(a0, r_a) * cut(tip.sketch),
            upright(a_lock) * cut(_padlock(False)), upright(a_open) * cut(_padlock(True))]


def entry_mark(r, angle, z_apex, w, h, depth, depth_apex=0.3):
    """Engraving tool for an upward-pointing triangle on a cylinder of radius r: apex at
    z_apex, centred at polar `angle` (deg). Its floor slopes from `depth` at the base to
    `depth_apex` at the tip, so it faces slightly down and reads as a shadowed dart."""
    pl = Plane(origin=(r + 1, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    face = pl * Polygon((-w / 2, z_apex - h), (w / 2, z_apex - h), (0, z_apex), align=None)
    prism = extrude(face, amount=r, dir=(-1, 0, 0))
    zb = z_apex - h
    floor = extrude_xz([(r - depth, zb - 2), (r + 2, zb - 2), (r + 2, z_apex + 1),
                        (r - depth_apex, z_apex + 1), (r - depth_apex, z_apex),
                        (r - depth, zb)], -w, w)
    return Rot(0, 0, angle) * (prism & floor)


def lanyard_lug(r, angle, proj, width, height, hole):
    """Block on the bed at the body's base with a 45-deg diamond cord hole (tangential)."""
    x0, x1 = r - 1.0, r + proj
    blk = extrude_xz([(x0, 0), (x1, 0), (x1, height), (x0, height)], -width / 2, width / 2)
    cx, cz, d = r + proj - 2.0 - hole / 2, height / 2, hole / 2
    hole_s = extrude_xz([(cx - d, cz), (cx, cz - d), (cx + d, cz), (cx, cz + d)], -width, width)
    return Rot(0, 0, angle) * (blk - hole_s)


def webbing_slot(r, angle, z0, web_w, gap, wall, mode):
    """Strap loop standing off the wall. Underside chamfered 45 deg, slot roof 45 deg.

    mode "belt": webbing runs horizontally (hip belt). "molle": vertically.
    Returns (add, cut); `cut` must not touch the case wall (stays at x >= r + 0.2).
    """
    x0, xi, xo = r - 1.5, r + 0.2, r + gap + wall
    sx = xo - x0                       # 45 deg underside rise
    if mode == "belt":
        zb = z0 + sx + 1.0
        zt = zb + web_w + 1.0
        ztop = zt + gap + wall
        half = 10.0
        add = extrude_xz([(x0, z0), (xo, z0 + sx), (xo, ztop), (x0, ztop)], -half, half)
        cut = extrude_xz([(xi, zb), (r + gap, zb), (r + gap, zt), (xi, zt + gap - 0.2)],
                         -half - 1, half + 1)
    else:
        half = web_w / 2 + 0.5 + wall
        ztop = z0 + sx + 30
        add = extrude_xz([(x0, z0), (xo, z0 + sx), (xo, ztop), (x0, ztop)], -half, half)
        cut = extrude_xz([(xi, z0 - 1), (r + gap, z0 - 1), (r + gap, ztop + 1), (xi, ztop + 1)],
                         -(web_w / 2 + 0.5), web_w / 2 + 0.5)
    rot = Rot(0, 0, angle)
    return rot * add, rot * cut


def label(lines, z, facing_up, max_w, depth, font=5.5, uniform=False, bold=True):
    """Engraving tool solid for text on a horizontal face at height z.

    facing_up: True for a face whose outward normal is +z (read from above).
    bold: strokes ~0.13 x font size (regular ~0.09), so 11.5 mm gives ~1.5 mm strokes, wide
    enough that a 0.6 mm nozzle keeps the gaps open on a bed-face engraving.
    Lines wider than max_w are scaled down to fit (measured, not estimated).
    """
    plane = Plane((0, 0, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1 if facing_up else -1))
    tools = []
    n = len(lines)
    style = FontStyle.BOLD if bold else FontStyle.REGULAR
    width = lambda t: Text(t, font_size=font, font_style=style).bounding_box().size.X
    sizes = [min(font, font * max_w / width(t)) for t in lines]
    if uniform:                     # every line at the size the longest one allows
        sizes = [min(sizes)] * n
    step = max(sizes) * 1.35
    for i, (t, fs) in enumerate(zip(lines, sizes)):
        y = (n - 1) / 2 * step - i * step
        sk = Text(t, font_size=fs, align=(Align.CENTER, Align.CENTER), font_style=style)
        tools.append(extrude(plane * Pos(0, y) * sk, amount=-(depth + 0.01)))
    out = tools[0]
    for t in tools[1:]:
        out += t
    # lift the tool 0.01 out of the face so the cut is clean
    return Pos(0, 0, 0.01 if facing_up else -0.01) * out


def desiccant_pocket(dia, z_top, depth):
    return Pos(0, 0, z_top - depth) * Cylinder(dia / 2, depth + 0.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
