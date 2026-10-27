"""Case builders.

fixed_case(...)        - any single lens configuration: body + lid.
telescoping_case(...)  - several configurations: body + sliding/screwing top tube (+ lock ring).

Parts are modelled in one assembled reference frame (use orientation, z up, body floor
bottom at z=0, axis = z). Each part carries the transform to its print orientation, each
pose the extra transforms that move parts into that configuration.
"""
import math
from dataclasses import dataclass, field

import numpy as np
from build123d import Plane, Pos, Rot, mirror

import params as P
from geometry.bayonet import channel, j_slot, lead_in, pins
from geometry.contents import contents
from geometry.features import (arc_cuts, desiccant_pocket, entry_mark, grip_flutes, label, lanyard_lug,
                               lock_arrow, webbing_slot)
from geometry.prims import revolve_rz
from geometry.thread import ridge_width, thread

STYLES = ("bayonet", "threaded", "tpu", "tpu_bayonet")   # tpu*: no foam, printed in TPU
TELE_ONLY = ("tpu_bayonet",)                              # styles built for case 1 only


def up(x, step=0.5):
    return math.ceil(x / step - 1e-9) * step


def bore_for(req_dia, snap=True):
    # >= 0.15 over requirement so the faceted STL (0.05 mm radial chord sag) still clears it;
    # with foam, snapped to a standard size class so lids are shared between cases (a smaller
    # lens gets a thicker sleeve); bare cases fit their lens
    need = req_dia + 0.15
    classes = sorted(P.BORE_CLASSES) if snap else []
    return next((b for b in classes if b >= need), up(need, 0.1))


@dataclass
class Xf:
    """dz after rz after an optional 180-degree flip about X."""
    dz: float = 0.0
    rz: float = 0.0
    flip: bool = False

    def loc(self):
        l = Pos(0, 0, self.dz) * Rot(0, 0, self.rz)
        return l * Rot(180, 0, 0) if self.flip else l

    def matrix(self):
        c, s = math.cos(math.radians(self.rz)), math.sin(math.radians(self.rz))
        T = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, self.dz], [0, 0, 0, 1.0]])
        F = np.diag([1, -1, -1, 1.0]) if self.flip else np.eye(4)
        return T @ F


@dataclass
class Variant:
    name: str
    case: str
    style: str
    kind: str
    title: str
    parts: dict                     # name -> (solid in assembled frame, Xf to print)
    poses: list                     # dicts: name, cfg, target, transforms {part: Xf}
    explode: dict                   # part -> Xf
    dims: dict = field(default_factory=dict)
    stop_pairs: list = field(default_factory=list)   # parts that seat on each other, not slide
    groove_walls: dict = field(default_factory=dict)  # part -> min wall outside the J-slot


def _fuse(base, extra):
    for s in extra:
        base = base + s
    return base


def _cut(base, extra):
    for s in extra:
        base = base - s
    return base


def _floor(end=P.END_CAP):
    return end + P.LABEL_DEPTH + (P.DESICCANT_DEPTH if P.DESICCANT_POCKET else 0)


def _body_profile(r_in, r_out, r_env, f, z_band0, z_band1, rim, r_low):
    """Body cup (r, z, fillet): rounded bed edge, lower body at r_low, filleted 45-deg taper
    out to a grip band flush with the lid (r_env); above the band (fixed cases) the wall
    steps in to r_out under the lid skirt. The taper is the band's underside, so it prints.
    With r_low == r_env there is no taper: the body is one full-diameter tube."""
    ch, fb, fe = P.EDGE_CHAMFER, P.BED_FILLET, P.EDGE_FILLET
    taper = r_env - r_low
    if taper < 1e-6:
        pts = [(0, 0), (r_env - ch, 0), (r_env, ch, fb), (r_env, z_band1, fe)]
    else:
        ft = min(2.0, taper)
        pts = [(0, 0), (r_low - ch, 0), (r_low, ch, fb),
               (r_low, z_band0 - taper, ft), (r_env, z_band0, ft), (r_env, z_band1, fe)]
    if z_band1 < rim - 1e-6:          # fixed case: steps in under the lid skirt
        pts += [(r_out, z_band1), (r_out, rim - 0.5), (r_out - 0.5, rim)]
    return pts + [(r_in + 0.5, rim), (r_in, rim - 0.5), (r_in, f), (0, f)]


def _closed_end(r_in_open, r_env, z_open_end, z_inner, z_outer):
    """Closed end as (r, z, fillet) points from the open side's wall to the axis:
    true fillet where the wall meets the open end, rounded chamfer on the bed face."""
    ch, fb, fe = P.EDGE_CHAMFER, P.BED_FILLET, P.EDGE_FILLET
    s = 1 if z_outer > z_inner else -1
    return [(r_env, z_open_end, fe), (r_env, z_outer - s * ch, fb), (r_env - ch, z_outer),
            (0, z_outer), (0, z_inner)]


def _cut_angles(n):
    return [P.CUT_ANGLE0 + i * 360 / n for i in range(n)]


def _flutes(part, r_env, z0, z1, mark_apex=None, cuts_from=None):
    """Grip flutes all round except under the concave cuts, then the cuts, full height.
    Every full-diameter part gets the cuts at the same angles, so they line up (lid on
    band, top tube on body) when the case is locked or closed.

    mark_apex (bayonet body bands): engrave the entry triangle, apex at that height, where
    a lid / top-tube cut sits at insertion (a twist anticlockwise of the locked cuts).
    cuts_from: the cuts stop below this height."""
    skip = _cut_angles(P.CUT_ARCS)
    a_mark = P.CUT_ANGLE0 + P.BAYONET_TWIST_DEG
    mark = mark_apex is not None and P.ENTRY_MARK
    if mark:   # leave out the flute(s) under the triangle
        half = math.degrees((P.ENTRY_MARK_W / 2 + P.FLUTE_W) / r_env)
        skip += [P.CUT_ANGLE0 + i * 360 / P.GRIP_FLUTES for i in range(P.GRIP_FLUTES)
                 if abs((i * 360 / P.GRIP_FLUTES - P.BAYONET_TWIST_DEG + 180) % 360 - 180) < half]
    part = part - grip_flutes(r_env, z0, z1, P.GRIP_FLUTES, P.FLUTE_DEPTH, P.FLUTE_W,
                              skip=skip, phase=P.CUT_ANGLE0)
    if mark:
        part = part - entry_mark(r_env, a_mark, mark_apex, P.ENTRY_MARK_W, P.ENTRY_MARK_H,
                                 P.ENTRY_MARK_DEPTH)
    cuts = arc_cuts(r_env, _cut_angles(P.CUT_ARCS), P.CUT_CHORD, P.CUT_DEPTH)
    if cuts_from is not None:
        keep = revolve_rz([(0, cuts_from), (r_env + 10, cuts_from), (r_env + 10, 4000), (0, 4000)])
        cuts = [c & keep for c in cuts]
    return _cut(part, cuts)


def _lower_cuts(body, r_low, r_env, z_end):
    """The same concave cuts around the lower body, ending at z_end with a 45 deg runout.
    Where the lower body is full diameter the upper cuts already run through it."""
    angles = _cut_angles(P.LOWER_CUTS)
    if r_low > r_env - P.CUT_DEPTH:
        up_ = _cut_angles(P.CUT_ARCS)
        angles = [a for a in angles if min(abs((a - u + 180) % 360 - 180) for u in up_) > 1]
    return _cut(body, arc_cuts(r_low, angles, P.CUT_CHORD, P.CUT_DEPTH, z_end))


def _top_symbols(part, z, r_env, from_below=False):
    """Lock arrow on the top face at z, or (from_below) on the base at z = 0, mirrored so it
    reads the same seen from below: clockwise there is the way to turn the base to lock."""
    if not P.LOCK_ARROW:
        return part
    if not from_below:
        return _cut(part, lock_arrow(z, r_env, P.LABEL_DEPTH))
    return _cut(part, [mirror(mirror(t, about=Plane.XY), about=Plane.XZ)
                       for t in lock_arrow(0.0, r_env, P.LABEL_DEPTH)])


def _body_extras(body, r_out, f, lines):
    if P.LANYARD_LUG:
        body = body + lanyard_lug(r_out, 180, P.LUG_PROJ, P.LUG_W, P.LUG_H, P.LUG_HOLE)
    if P.WEBBING_SLOT:
        add, cut = webbing_slot(r_out, 90, P.EDGE_CHAMFER + 1, P.WEBBING_W, P.WEBBING_GAP,
                                P.WALL, P.WEBBING_MODE)
        body = body + add - cut
    if P.DESICCANT_POCKET:
        body = body - desiccant_pocket(P.DESICCANT_DIA, f, P.DESICCANT_DEPTH)
    if not lines:
        return body
    # base text: one size on every case, inside the bed chamfer
    return body - label(lines, 0, False, 2 * (r_out - P.WALL) * 0.85, P.LABEL_DEPTH, P.LABEL_FONT_BASE,
                        uniform=True)


def _base_lines(cfgs):
    """Lens details for the base: mount + range per lens, then the f-number (once if the
    lenses share it); "+ ADAPTER" when every configuration carries the adapter."""
    lenses = list(dict.fromkeys(i for c in cfgs for i in c.items if len(i.base) == 2))
    fnos = list(dict.fromkeys(i.base[1] for i in lenses))
    lines = ([i.base[0] for i in lenses] + fnos if len(fnos) == 1
             else [s for i in lenses for s in i.base])
    adapters = [i for i in cfgs[0].items if len(i.base) == 1]
    return lines + [a.base[0] for a in adapters if all(a in c.items for c in cfgs)]


# ------------------------------------------------------------------ fixed length
def fixed_case(name, cfg, style, lines=None):
    bay = style == "bayonet"
    lines = lines or _base_lines([cfg])
    foam = not style.startswith("tpu")
    req_len, req_dia = cfg.need(foam)
    bore, target = bore_for(req_dia, foam), up(req_len)
    r_in = bore / 2
    if not foam:
        wall = P.WALL_TPU
    else:
        wall = P.WALL_THICK if name in P.THICK_WALL_CASES else P.WALL
    r_b = r_in + wall
    f, lt = _floor(), P.END_CAP + P.LABEL_DEPTH
    n = P.BAYONET_NOTCH if bay else 0.0
    rim = f + target - n                  # bayonet: lid seats n above the rim (J hook)
    zc = rim + n                          # lid ceiling
    zt = zc + lt                          # lid top
    w = ridge_width(P.THREAD_PITCH, P.THREAD_DEPTH, P.THREAD_CLEAR, P.THREAD_FLANK_GAP)
    thread_len = P.THREAD_ENGAGE * P.THREAD_PITCH + w
    engage = P.LID_ENGAGE if bay else max(P.LID_ENGAGE, thread_len + 3.0)
    zr = zc - engage                      # lid rim
    if bay:
        r_li = r_b + P.SLIDE_CLEAR
        r_lo = r_li + P.GROOVE_DEPTH + P.BAYONET_OUTER_WALL
    else:
        r_li = r_b + P.THREAD_DEPTH + P.THREAD_CLEAR    # internal-thread base
        r_lo = r_li + (wall if foam else P.WALL_TPU_LID)
    r_env = r_lo + P.FLUTE_DEPTH           # outer envelope: lid and body grip band
    z_b1 = zr - n - 0.5                   # band top clears the lid rim during the twist
    z_b0 = z_b1 - P.GRIP_BAND
    r_low = r_b + (P.CUT_DEPTH if P.LOWER_CUTS else 0.0)   # lower body: thicker by any cut depth
    body = revolve_rz(_body_profile(r_in, r_b, r_env, f, z_b0, z_b1, rim, r_low))
    lid = revolve_rz([(r_li, zc), (r_li, zr + 0.8), (r_li + 0.8, zr)]
                     + _closed_end(r_li, r_env, zr, zc, zt))

    if bay:
        zp_t = rim - 2.0
        zp_b = zp_t - P.PIN_HEIGHT
        proj = P.SLIDE_CLEAR + P.GROOVE_DEPTH - P.PIN_RADIAL_GAP
        body = _fuse(body, pins(r_b, zp_b, zp_t, proj, "bottom", P.BAYONET_PINS, P.PIN_WIDTH))
        voids, bumps = j_slot(r_b, r_li, P.GROOVE_DEPTH, zp_b, zp_t, "bottom", P.PIN_AXIAL_CLEAR,
                              P.BAYONET_PINS, P.PIN_WIDTH, P.BAYONET_TWIST_DEG, n, +1,
                              channel_to=zr - 1, bump_h=P.DETENT_BUMP_H, bump_r=P.DETENT_BUMP_R)
        half = math.degrees((P.PIN_WIDTH / 2 + P.PIN_AXIAL_CLEAR) / r_b)
        # one ramp per channel, on its clockwise side (the pin arrives from there as the lid
        # turns clockwise to lock); the anticlockwise side, toward its own lock slot, stays
        # vertical. Past the neighbouring channel's lock slot the ramp must pass below it.
        k = math.tan(math.radians(P.LEAD_IN_ANGLE))
        pitch = math.radians(360 / P.BAYONET_PINS) * r_li
        gap = pitch - 2 * math.radians(half) * r_li                   # between channel edges
        clear = pitch - math.radians(P.BAYONET_TWIST_DEG + 2 * half) * r_li - P.LEAD_IN_LAND
        under = (zp_b + n - P.PIN_AXIAL_CLEAR + 0.1 - zr - P.LEAD_IN_LAND) / k
        len_ramp = min(gap, (zc - zr - P.LEAD_IN_LAND) / k, clear + under)
        # the lead-in is built at -twist directly (mirroring it breaks the detent fuse)
        mouths = [Rot(0, 0, i * 360 / P.BAYONET_PINS)
                  * lead_in(r_li, P.GROOVE_DEPTH, -P.BAYONET_TWIST_DEG, half, zr, 0.0, len_ramp,
                            P.LEAD_IN_ANGLE, +1)
                  for i in range(P.BAYONET_PINS)]
        # mirrored so the lid locks clockwise seen from above, like a jar lid
        voids = [mirror(s, about=Plane.XZ) for s in voids]
        bumps = [mirror(s, about=Plane.XZ) for s in bumps]
        lid = _cut(_fuse(_cut(lid, voids), bumps), mouths)
    else:
        z_to = rim - 1.0
        z_from = z_to - thread_len
        body = _fuse(body, thread(r_b, P.THREAD_DEPTH, P.THREAD_PITCH, P.THREAD_STARTS, z_from, z_to,
                                  z_from, False, w))
        lid = _fuse(lid, thread(r_li, P.THREAD_DEPTH, P.THREAD_PITCH, P.THREAD_STARTS, max(z_from - P.THREAD_PITCH, zr + 1.0),
                                zc - 0.5, z_from + P.THREAD_PITCH / 2, True, w))

    body = _flutes(body, r_env, z_b0 - 2, z_b1 + 1, z_b1 - 1.5 if bay else None)
    body = _lower_cuts(body, r_low, r_env, z_b0 - (r_env - r_low) - 1.3)
    body = _body_extras(body, r_b, f, lines)
    lid = _flutes(lid, r_env, zr - 1, zt + 1)
    lid = _top_symbols(lid, zt, r_env)
    # the lid depends only on bore + wall + style, so lids are interchangeable between bodies of
    # the same size: its size code is engraved inside, on the ceiling, out of sight
    # (off the axis, where the verifier measures the interior length)
    code = f"Ø{bore:.0f}" + (f"/{wall:.0f}" if foam and wall != P.WALL else "")
    lid = lid - Pos(0, -r_li * 0.5, 0) * label([code], zc, False, r_li * 0.6, P.LABEL_DEPTH, 12.0)

    v = Variant(name=f"{name}_{style}", case=name, style=style, kind="fixed",
                title=f"{name} {style}: {cfg.short}",
                parts={"body": (body, Xf()), "lid": (lid, Xf(dz=zt, flip=True))},
                poses=[dict(name=cfg.label, cfg=cfg, target=target, transforms={},
                            req_len=req_len, req_dia=req_dia,
                            visual=contents(cfg, bore, f, zc, foam))],
                explode={"lid": Xf(dz=engage + 35, rz=P.BAYONET_TWIST_DEG if bay else 0)},
                groove_walls={"lid": P.BAYONET_OUTER_WALL} if bay else {})
    v.dims = dict(bore=bore, od=2 * r_env, od_features=2 * r_env,
                  length=zt, length_ext=None, lug=P.LUG_PROJ if P.LANYARD_LUG else 0)
    return v


# ------------------------------------------------------------------ telescoping
def telescoping_case(name, cfgs, style):
    """Body (closed floor) + top tube (closed top, grip flange) that slides into it.

    bayonet: J-track with one twist-lock position per config.
    threaded: full-length 2-start thread, lock ring jams on the body rim; index marks.
    """
    bay = style in ("bayonet", "tpu_bayonet")
    foam = not style.startswith("tpu")
    tb = style == "tpu_bayonet"
    bare = P.TPU_BAYONET_GAP if tb else P.BARE_GAP
    end = P.TPU_BAYONET_END if tb else P.END_CAP
    reqs = [c.need(foam, bare) for c in cfgs]
    wall = (P.WALL_THICK if name in P.THICK_WALL_CASES else P.WALL) if foam else (
        P.TPU_BAYONET_WALL if tb else P.WALL_TPU)
    bore = bore_for(max(d for _, d in reqs), foam)
    targets = [up(l) for l, _ in reqs]
    deltas = [t - targets[0] for t in targets]
    r_in = bore / 2
    r_i = r_in + (P.TELE_INNER_WALL if foam else wall)   # top tube outer (thread root)
    f, lt = _floor(end), end + P.LABEL_DEPTH
    # bayonet features: TPU is soft, so its pins, groove, notch and bump are bigger and its gaps looser
    s, e = (1.0, 0.0) if foam else (P.TPU_BAYONET_SCALE, P.TPU_EXTRA_CLEAR)
    slide, pin_gap, pin_clear = P.SLIDE_CLEAR + e, P.PIN_RADIAL_GAP + e, P.PIN_AXIAL_CLEAR + e
    groove, pin_w, outer = P.GROOVE_DEPTH * s, P.PIN_WIDTH * s, P.BAYONET_OUTER_WALL * s
    if tb:
        outer += P.TPU_BAYONET_WALL - P.WALL_TPU      # thicker sides on the body too
    bump_h, bump_r = pin_gap + (P.DETENT_BUMP_H - P.PIN_RADIAL_GAP) * s, P.DETENT_BUMP_R * s
    if bay:
        n = P.BAYONET_NOTCH * s
        r_bi = r_i + slide
        r_bo = r_bi + groove + outer
        z_open = f + n                          # leg of position 1 reaches the floor
        h_t = targets[0] - n
    else:
        n = 0.0
        r_bi = r_i + P.THREAD_DEPTH + P.THREAD_CLEAR   # internal-thread base
        r_bo = r_bi + wall
        z_open = f + 0.5
        h_t = targets[0] - 0.5
    z_ceil = z_open + h_t
    z_top = z_ceil + lt
    z_fl = z_top - P.FLANGE_H                   # flange underside, position 1
    rim = z_fl - n - 0.5 - (0 if bay else P.RING_H)

    r_env = r_bo + P.FLUTE_DEPTH           # grip band, flange and ring are flush at r_env
    z_b0 = rim - P.TELE_GRIP_BAND
    # lower body: plain cylinder at r_bo (the J-track runs down it, so its wall outside the
    # groove is BAYONET_OUTER_WALL), stepping out at 45 deg to the fluted grip band
    body = revolve_rz(_body_profile(r_bi, r_bo, r_env, f, z_b0, rim, rim, r_bo))
    inner = revolve_rz([(r_in, z_ceil), (r_in, z_open + 0.5), (r_in + 0.5, z_open),
                        (r_i - 0.5, z_open), (r_i, z_open + 0.5), (r_i, z_fl)]
                       + _closed_end(r_i, r_env, z_fl, z_ceil, z_top))
    parts, stop_pairs = {}, []
    if bay:
        zp_b = z_open + 1.0
        zp_t = zp_b + P.PIN_HEIGHT
        proj = slide + groove - pin_gap
        inner = _fuse(inner, pins(r_i, zp_b, zp_t, proj, "top", P.BAYONET_PINS, pin_w))
        half = math.degrees((pin_w / 2 + pin_clear) / r_i)
        for d in deltas:
            voids, bumps = j_slot(r_i, r_bi, groove, zp_b + d, zp_t + d, "top",
                                  pin_clear, P.BAYONET_PINS, pin_w,
                                  P.BAYONET_TWIST_DEG, n, -1, None,
                                  bump_h, bump_r)
            body = _fuse(_cut(body, voids), bumps)
        track = channel(r_bi, groove, zp_b - n - pin_clear, rim + 1,
                        P.BAYONET_TWIST_DEG, half)
        # one ramp per channel, on its anticlockwise side (the pin arrives from there as the
        # top turns clockwise to lock); the side over its own lock legs stays vertical. Past
        # the neighbouring channel's legs the ramp must stay above the top one.
        k = math.tan(math.radians(P.LEAD_IN_ANGLE))
        pitch = math.radians(360 / P.BAYONET_PINS) * r_bi
        gap = pitch - 2 * math.radians(half) * r_bi                   # between channel edges
        clear = pitch - math.radians(P.BAYONET_TWIST_DEG + 2 * half) * r_bi - P.LEAD_IN_LAND
        over = (rim - (zp_t + deltas[-1] + pin_clear) - P.LEAD_IN_LAND) / k
        len_ramp = min(gap, clear + over)
        mouth = lead_in(r_bi, groove, P.BAYONET_TWIST_DEG, half, rim, len_ramp, 0.0,
                        P.LEAD_IN_ANGLE, -1)
        body = _cut(body, [Rot(0, 0, i * 360 / P.BAYONET_PINS) * s
                           for i in range(P.BAYONET_PINS) for s in (track, mouth)])
        pose_xf = [dict(inner=Xf(dz=d)) for d in deltas]
    else:
        st = P.TELE_THREAD_STARTS
        lead = P.THREAD_PITCH * st
        w = ridge_width(P.THREAD_PITCH, P.THREAD_DEPTH, P.THREAD_CLEAR, P.THREAD_FLANK_GAP)
        phase = z_open + 0.5
        inner = _fuse(inner, thread(r_i, P.THREAD_DEPTH, P.THREAD_PITCH, st, z_open + 0.5,
                                    z_fl - 0.3, phase, False, w))
        body = _fuse(body, thread(r_bi, P.THREAD_DEPTH, P.THREAD_PITCH, st, f + 0.5, rim - 0.3,
                                  phase + P.THREAD_PITCH / 2, True, w))
        ch = P.EDGE_CHAMFER
        ring = revolve_rz([(r_bi, rim), (r_env - ch, rim), (r_env, rim + ch, P.BED_FILLET),
                           (r_env, rim + P.RING_H, P.EDGE_FILLET), (r_bi, rim + P.RING_H)])
        # ring thread: run past both faces, trim each start to the ring height, then fuse
        # (trimming after the fuse trips an OCCT boolean failure)
        trim = revolve_rz([(r_bi - P.THREAD_DEPTH - 1, rim), (r_bo + 2, rim),
                           (r_bo + 2, rim + P.RING_H), (r_bi - P.THREAD_DEPTH - 1, rim + P.RING_H)])
        ring = _fuse(ring, [t & trim for t in thread(
            r_bi, P.THREAD_DEPTH, P.THREAD_PITCH, st, rim - lead, rim + P.RING_H + lead,
            phase + P.THREAD_PITCH / 2, True, w)])
        ring = _flutes(ring, r_env, rim - 1, rim + P.RING_H + 1)
        # index marks: V-notches in the thread crests where the ring's top edge sits for
        # each position; position k is marked with k dashes
        r_c = r_i + P.THREAD_DEPTH
        for k, d in enumerate(deltas):
            z = rim + P.RING_H - d
            v = [(r_c + 0.5, z - 1.5), (r_c - 1.0, z), (r_c + 0.5, z + 1.5)]
            for j in range(k + 1):
                a = 90 + (j - k / 2) * 8
                inner = inner - (revolve_rz(v, a - 2.5, a + 2.5)
                                 & revolve_rz([(0, 0), (r_bo, 0), (r_bo, z_fl - 0.2), (0, z_fl - 0.2)]))
        parts["ring"] = (ring, Xf(dz=-rim))
        stop_pairs = [["body", "ring"]]
        pose_xf = [dict(inner=Xf(dz=d, rz=d / lead * 360)) for d in deltas]

    # flute floors are flush with the lower body here, so they stop half way down the taper
    body = _flutes(body, r_env, z_b0 - P.FLUTE_DEPTH / 2, rim + 1, rim - 1.5 if bay else None,
                   cuts_from=z_b0 - (r_env - r_bo))
    # lock arrow on the base (the body is the part you hold and turn), lens details on the
    # top; positions click in shortest-first (threaded: k dashes)
    body = _top_symbols(_body_extras(body, r_bo, f, []), 0.0, r_bo, from_below=True)
    inner = _flutes(inner, r_env, z_fl - 1, z_top + 1)
    inner = inner - label(_base_lines(cfgs), z_top, True, 2 * r_in * 0.85, P.LABEL_DEPTH,
                          P.LABEL_FONT_BASE, uniform=True)

    parts = {"body": (body, Xf()), "inner": (inner, Xf(dz=z_top, flip=True)), **parts}
    explode = {"inner": Xf(dz=rim - z_open + 30)}
    if "ring" in parts:
        explode["ring"] = Xf(dz=14)
    v = Variant(name=f"{name}_{style}", case=name, style=style, kind="telescoping",
                title=f"{name} {style}: telescoping " + " / ".join(c.short for c in cfgs),
                parts=parts,
                poses=[dict(name=c.label, cfg=c, target=t, transforms=x,
                            req_len=rq[0], req_dia=rq[1], visual=contents(c, bore, f, z_ceil + d, foam, bare))
                       for c, t, x, d, rq in zip(cfgs, targets, pose_xf, deltas, reqs)],
                explode=explode, stop_pairs=stop_pairs,
                groove_walls={"body": outer} if bay else {})
    v.dims = dict(bore=bore, od=2 * r_env, od_features=2 * r_env,
                  length=z_top, length_ext=z_top + deltas[-1],
                  overlap_min=rim - (z_open + deltas[-1]), lug=P.LUG_PROJ if P.LANYARD_LUG else 0)
    return v


def all_variants(only=None):
    builders = {
        "case1": lambda s: telescoping_case("case1", P.CASE1_CONFIGS, s),
        "case2": lambda s: fixed_case("case2", P.CASE2_CONFIG, s),
        "case3": lambda s: fixed_case("case3", P.CASE3_CONFIG, s),
        "case4": lambda s: fixed_case("case4", P.CASE4_CONFIG, s),
        "case5": lambda s: fixed_case("case5", P.CASE5_CONFIG, s),
        "case6": lambda s: fixed_case("case6", P.CASE6_CONFIG, s),
    }
    for case, b in builders.items():
        for s in STYLES:
            if s in TELE_ONLY and case != "case1":
                continue
            if only is None or f"{case}_{s}" in only or case in only:
                yield b(s)
