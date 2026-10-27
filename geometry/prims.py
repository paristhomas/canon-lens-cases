"""Low-level helpers. Everything is built around the z axis; profiles are (r, z) lists."""
import math

from build123d import Axis, Plane, Polygon, Rot, revolve, extrude


def round_poly(pts, seg=8):
    """Polygon with rounded corners. pts: (x, y) or (x, y, radius); radius 0 = sharp."""
    pts = [(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in pts]
    out = []
    n = len(pts)
    for i, (x, y, r) in enumerate(pts):
        if r <= 0:
            out.append((x, y))
            continue
        ax, ay = pts[i - 1][:2]
        bx, by = pts[(i + 1) % n][:2]
        ux, uy = ax - x, ay - y
        vx, vy = bx - x, by - y
        lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
        ux, uy, vx, vy = ux / lu, uy / lu, vx / lv, vy / lv
        th = math.acos(max(-1.0, min(1.0, ux * vx + uy * vy)))
        t = r / math.tan(th / 2)
        assert t <= min(lu, lv) + 1e-6, f"fillet r={r} too big at {(x, y)}"
        p0 = (x + ux * t, y + uy * t)
        p1 = (x + vx * t, y + vy * t)
        bxs, bys = ux + vx, uy + vy
        lb = math.hypot(bxs, bys)
        d = r / math.sin(th / 2)
        cx, cy = x + bxs / lb * d, y + bys / lb * d
        a0 = math.atan2(p0[1] - cy, p0[0] - cx)
        a1 = math.atan2(p1[1] - cy, p1[0] - cx)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(cx + r * math.cos(a0 + da * k / seg), cy + r * math.sin(a0 + da * k / seg))
                for k in range(seg + 1)]
    return out


def revolve_rz(pts, a0=0.0, a1=360.0):
    """Revolve an (r, z) polygon about Z from angle a0 to a1 (degrees, CCW).

    Points may carry a third value, a corner fillet radius (see round_poly).
    """
    if any(len(p) > 2 for p in pts):
        pts = round_poly(pts)
    face = Plane.XZ * Polygon(*pts, align=None)
    arc = a1 - a0
    solid = revolve(face, axis=Axis.Z, revolution_arc=arc)
    return Rot(0, 0, a0) * solid if a0 else solid


def extrude_xz(pts, y0, y1):
    """Extrude an (x, z) polygon along +Y from y0 to y1."""
    face = Plane.XZ.offset(-y0) * Polygon(*pts, align=None)   # Plane.XZ normal is -Y
    return extrude(face, amount=-(y1 - y0))
