"""Coarse 45-degree-flank trapezoidal thread (helical sweep), external or internal.

Mating pair: an external thread with root radius r and an internal thread with base radius
r + depth + clear, both with the same pitch/starts, interleave when the internal phase is
the external phase + pitch / 2.
"""
import math

from build123d import Helix, Plane, Polygon, Rot, sweep

EMBED = 0.3   # how far the ridge base sinks into the wall so the union is clean


def ridge_width(pitch, depth, clear, flank_gap):
    """Root width of each ridge so a mating pair leaves `flank_gap` axially."""
    w = (pitch + 2 * depth + 2 * clear) / 2 - flank_gap
    assert w - 2 * depth > 0.2, "thread crest too narrow; reduce depth or increase pitch"
    return w


def thread(r_base, depth, pitch, starts, z_from, z_to, phase, internal, width):
    """Helical ridges on a wall surface at radius r_base.

    phase: z of a ridge's lower root edge at angle 0 (defines the helix family).
    The ridges fill [z_from, z_to] as far as whole helix starts allow.
    """
    lead = pitch * starts
    # at a fixed angle the ridges of all starts sit one pitch apart, so any of them can begin
    # the run: start at the first one above z_from (the copies are rotated, not lifted)
    k = math.ceil((z_from - phase) / pitch - 1e-9)
    z0 = phase + k * pitch
    length = z_to - width - z0
    if length <= 0:
        raise ValueError("thread zone too short")
    e, h, w = EMBED, depth, width
    if internal:
        rb, rc = r_base + e, r_base - h
    else:
        rb, rc = r_base - e, r_base + h
    # 45 deg flanks: axial change == radial change; the embedded base is widened to match
    prof = [(rb, z0 - e), (rb, z0 + w + e), (rc, z0 + w - h), (rc, z0 + h)]
    face = Plane.XZ * Polygon(*prof, align=None)
    path = Helix(pitch=lead, height=length, radius=rb, center=(0, 0, z0))
    one = sweep(face, path=path, is_frenet=True)
    return [Rot(0, 0, i * 360 / starts) * one for i in range(starts)]
