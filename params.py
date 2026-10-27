"""All dimensions, allowances and clearances for the lens cases (mm).

Tags in comments:
  [SPEC] manufacturer published figure
  [EST]  estimate - measure and update
  [DES]  design choice
"""
from dataclasses import dataclass, field


# ---------------------------------------------------------------- lenses
@dataclass(frozen=True)
class Item:
    name: str
    dia: float      # max diameter
    length: float   # mount -> front, retracted, no caps
    short: str = ""  # label text
    front_dia: float = 0.0  # front cap diameter (filter size + ~2), proxy model only
    base: tuple = ()  # base engraving: (mount + range, f-number), or ("+ ADAPTER",)
    front_cap: float | None = None  # front cap protrusion if not FRONT_CAP
    foam_less: float = 0.0  # end foam given up for this lens in the foam styles (see L2)


L1 = Item("EF-S 18-55mm f/4-5.6 IS STM", 66.5, 61.8, "18-55", 60.0, ("EF-S 18-55", "f/4-5.6"))  # [SPEC] dims; front cap dia est. (58 mm filter)
L2 = Item("EF-S 55-250mm f/4-5.6 IS STM", 70.0, 113.2, "55-250", 60.0, ("EF-S 55-250", "f/4-5.6"),
          foam_less=2.0)  # [SPEC] dia, 111.2 spec length; [MEAS] ~2 mm longer in use. The foam cases were
                          # printed for 111.2 and fit well with 2 mm less end foam: keep them that length.
                          # front cap dia est. (58 mm filter)
L3 = Item("EF 50mm f/1.8 STM", 69.2, 39.3, "EF 50 f/1.8", 51.0, ("EF 50", "f/1.8"),
          front_cap=5.0)  # [SPEC] dims; front cap dia est. (49 mm filter); cap [MEAS]: the first print was ~1 mm long
L4 = Item("RF 100-400mm F5.6-8 IS USM", 79.5, 164.7, "RF 100-400", 69.0, ("RF 100-400", "f/5.6-8"))  # [SPEC] dims; front cap dia est. (67 mm filter)
A1 = Item("Mount Adapter EF-EOS R", 71.2, 24.0, "ADAPTER", 0.0, ("+ ADAPTER",))         # [SPEC]

# ---------------------------------------------------------------- caps
FRONT_CAP = 6.0         # [EST] front cap protrusion
EF_REAR_CAP = 12.0      # [EST] EF rear cap
RF_REAR_CAP = 10.0      # [EST] RF dust cap (on A1 rear or on L4)
EF_REAR_CAP_DIA = 62.0  # [EST] proxy model only
RF_REAR_CAP_DIA = 66.0  # [EST] proxy model only
HOOD_REVERSED_DIA = 85.0  # [EST] ET-74B reversed over L4 barrel
L4_WITH_HOOD = False      # [DES] store hood reversed in case 3

# ---------------------------------------------------------------- packing
FOAM_RADIAL = 2.25      # [DES] foam each side (3.0 printed bulky)
FOAM_END_BOTTOM = 8.0   # [DES] foam under the rear cap (takes the drop when set down)
FOAM_END_TOP = 5.0      # [DES] foam over the front cap
FIT_CLEAR_DIA = 1.0     # [DES] extra on diameter, on top of foam
BARE_GAP = 1.0          # [DES] tpu style (no foam): lens to case, all round and at each end

# ---------------------------------------------------------------- print / fit
WALL = 2.0              # [DES] min tube wall anywhere (thread roots, flute floors) ...
WALL_THICK = 3.0        # [DES] ... but this on the telescoping case and the fixed cases for the two
THICK_WALL_CASES = ("case1", "case3", "case5")   # longest lenses (2 mm looked too thin there)
TELE_INNER_WALL = 2.5   # [DES] case 1 top tube (foam styles)
WALL_TPU = 4.0          # [DES] tpu style: threaded, printed in TPU, no foam; its tube walls ...
WALL_TPU_LID = 2.0      # [DES] ... except a fixed lid's wall outside its thread (4 mm through the
                        #       2 mm ridges; it sets the grip diameter)
BAYONET_OUTER_WALL = 2.0  # [DES] ... except outside the bayonet J-slot (measured from the groove floor)
END_CAP = 4.0           # [DES] min floor / lid thickness (ends take the drop impacts)
# print tolerance: every mating gap is >= 0.2 mm measured square to the surfaces
SLIDE_CLEAR = 0.3       # [DES] radial, sliding fits (lid on body, top tube in body); 0.4 printed loose
MIN_PRINT_GAP = 0.2     # [DES] smallest allowed gap between mating parts, checked by verify.py
THREAD_CLEAR = 0.4      # [DES] radial, thread crest to root (0.5 printed a touch loose)
MAX_OVERHANG_DEG = 45.0  # [DES] from vertical
RATTLE_MAX = 3.0        # [DES] case-1 position may exceed requirement by this

# ---------------------------------------------------------------- joints
# thread: 45 deg flanks (90 deg included) so both external and internal threads print
# unsupported in any orientation
THREAD_PITCH = 6.0      # [DES] axial ridge spacing, >= 3 mm (coarse: robust, grit-tolerant)
THREAD_DEPTH = 2.0      # [DES] radial ridge height
THREAD_FLANK_GAP = 0.4  # [DES] axial flank clearance (= 0.28 mm normal to the 45 deg flanks)
THREAD_ENGAGE = 1.5     # [DES] fixed-case lid engagement, in pitches (9 mm of thread)
THREAD_STARTS = 2       # [DES] fixed-case lid: 2-start -> lead 12 mm, closes in 3/4 turn; 2 so either
                        #       start ends with the cuts lined up (they repeat every 90 deg)
TELE_THREAD_STARTS = 2  # [DES] telescoping thread: 2-start -> lead 12 mm, ~4 turns 1->3
RING_H = 8.0            # [DES] telescoping lock ring height

BAYONET_PINS = 8        # [DES] (entry every 45 deg; 4 pins: one snapped off in a drop)
GROOVE_DEPTH = 2.0      # [DES] J-slot depth into the wall (pin hooks 1.6 mm past the mating wall)
PIN_RADIAL_GAP = 0.3    # [DES] pin tip to groove floor
PIN_WIDTH = 6.0         # [DES] circumferential
PIN_HEIGHT = 6.0        # [DES] axial, at the wall (4.0 snapped off in a drop)
PIN_AXIAL_CLEAR = 0.35  # [DES] pin to slot, axial and circumferential (0.25 normal to the 45 deg face)
BAYONET_TWIST_DEG = 25.0  # [DES] circumferential leg of the J
BAYONET_NOTCH = 1.5     # [DES] J hook depth; foam pushes the pin into it
DETENT_BUMP_H = 0.5     # [DES] bump height off the groove floor (0.2 mm interference: printed just right)
DETENT_BUMP_R = 1.0     # [DES] bump radius (vertical half-cylinder)
TPU_BAYONET_SCALE = 1.5  # [DES] case 1 tpu_bayonet (TPU, no foam): pin width, groove depth, hook notch,
                        #       bump radius and interference and the wall outside the groove are 1.5x
                        #       (TPU is soft). Pin height stays: taller legs would merge between positions
TPU_EXTRA_CLEAR = 0.1   # [DES] ... and its sliding / pin gaps are 0.1 mm looser
TPU_BAYONET_GAP = 0.5   # [DES] ... lens to case, all round and at each end (BARE_GAP elsewhere)
TPU_BAYONET_WALL = 4.5  # [DES] ... tube walls (WALL_TPU + 0.5)
TPU_BAYONET_END = 5.0   # [DES] ... floor and top (END_CAP + 1)
LID_ENGAGE = 16.0       # [DES] lid skirt length, fixed cases (threaded lids grow to fit the thread)
FLANGE_H = 8.0          # [DES] telescoping top-tube grip flange height (incl. cap)

# ---------------------------------------------------------------- features
# Backpack use: nothing protrudes past the lid diameter. Grip is recessed flutes cut into
# a slightly thicker lid wall and a body grip band flush with the lid; edges are rounded.
GRIP_FLUTES = 56        # [DES] count around circumference; they run out through both ends
FLUTE_DEPTH = 0.8       # [DES] recess depth (wall is thickened by this much)
FLUTE_W = 4.0           # [DES] flute width (scallop radius = FLUTE_W / 2)
GRIP_BAND = 10.0        # [DES] fluted band on fixed bodies, flush with the lid
TELE_GRIP_BAND = 20.0   # [DES] the same on the telescoping body
CUT_ARCS = 0            # [DES] off (printed: not effective, looked poor). Slightly concave full-height
                        #       anti-roll cuts on the lid and grip band, lined up when locked / closed
CUT_ANGLE0 = 45.0       # [DES] first cut (the flutes are phased to it)
CUT_CHORD = 15.0        # [DES] cut width at the surface
CUT_DEPTH = 0.8         # [DES] depth at the centre (= FLUTE_DEPTH, so walls keep their minimum)
LOWER_CUTS = 0          # [DES] fixed cases: the same cuts around the lower body (4 continue the upper
                        #       ones); the lower body is CUT_DEPTH thicker so its wall keeps WALL.
                        #       The telescoping body's lower section is a plain cylinder.
ENTRY_MARK = False      # [DES] off: the one-sided lead-ins close from any angle, and it lined up with
                        #       the cuts. Engraved triangle on the body band marking an entry
ENTRY_MARK_W = 9.0      # [DES] triangle base width
ENTRY_MARK_H = 7.0      # [DES] triangle height (sides 29 deg from vertical: prints)
ENTRY_MARK_DEPTH = 1.8  # [DES] at the base, sloping to 0.3 at the tip (the band wall is thick there)
LEAD_IN_ANGLE = 30.0    # [DES] bayonet entry ramps, from horizontal. One ramp per channel, on the side
                        #       the pin comes from when turning to lock; the lock side is vertical, so
                        #       push + turn clockwise always closes it, from any angle. They face the
                        #       rim, so they print. As long as fits under the neighbouring lock slots
LEAD_IN_LAND = 1.5      # [DES] solid wall kept between a ramp and the lock slot / lid ceiling
LOCK_ARROW = True       # [DES] clockwise arrow with open / closed padlocks on every top face
EDGE_CHAMFER = 2.0      # [DES] bed-side edges: 45 deg chamfer ...
BED_FILLET = 3.0        # [DES] ... with its upper corner rounded (prints without support)
EDGE_FILLET = 1.5       # [DES] other outside edges: true fillet
LABEL_DEPTH = 0.6       # [DES] engraving depth; caps carrying labels get this extra
LABEL_FONT = 8.0        # [DES] max font size (long lines shrink to fit)
LABEL_FONT_BASE = 11.5  # [DES] lens details on the body base, one size on every case (bold: ~1.5 mm
                        #       strokes for a 0.6 mm nozzle, 8.5 mm capitals; fits the smallest base)
LANYARD_LUG = False     # [DES] off: it sticks out (backpack use)
LUG_PROJ = 8.0          # [DES] lanyard lug radial projection
LUG_W = 14.0            # [DES] lanyard lug width
LUG_H = 12.0            # [DES]
LUG_HOLE = 4.5          # [DES] diamond (45 deg) hole, across flats-ish
WEBBING_SLOT = False    # [DES] 25 mm strap / MOLLE slot
WEBBING_MODE = "belt"   # [DES] "belt": webbing runs horizontally; "molle": vertically
WEBBING_W = 25.0        # [SPEC] standard webbing width
WEBBING_GAP = 4.0       # [DES] slot thickness for webbing
DESICCANT_POCKET = False  # [DES] pocket in the body floor
DESICCANT_DIA = 30.0    # [DES]
DESICCANT_DEPTH = 6.0   # [DES] adds to the floor thickness
CASE2_WITH_ADAPTER = False  # [DES] True -> L3 + adapter + RF rear cap
# Standard bore sizes: every fixed case whose lens fits uses the smallest class, so lids
# are interchangeable between them; a smaller lens just gets a thicker foam sleeve.
BORE_CLASSES = (77.0, 85.5)  # [DES] mm; a case that fits none gets its own bore

# ---------------------------------------------------------------- derived
@dataclass(frozen=True)
class Config:
    label: str
    items: tuple
    rear_cap: float
    dia_override: float | None = None
    stack_override: float | None = None   # generic position: any lens whose capped length fits
    short_override: str = ""

    @property
    def dia(self):
        d = max((i.dia for i in self.items), default=0)
        return max(d, self.dia_override or 0)

    @property
    def stack(self):
        if self.stack_override is not None:
            return self.stack_override
        return sum(i.length for i in self.items) + self.front_cap + self.rear_cap

    @property
    def front_cap(self):
        caps = [i.front_cap for i in self.items[:1] if i.front_cap is not None]
        return caps[0] if caps else FRONT_CAP

    @property
    def req_len(self):          # required interior length
        return self.stack + FOAM_END_BOTTOM + FOAM_END_TOP - self.foam_less

    @property
    def foam_less(self):
        return sum(i.foam_less for i in self.items)

    @property
    def short(self):
        return self.short_override or " + ".join(i.short for i in self.items)

    @property
    def req_dia(self):          # required interior diameter
        return self.dia + 2 * FOAM_RADIAL + FIT_CLEAR_DIA

    def need(self, foam=True, gap=BARE_GAP):
        """(length, diameter) required inside: with foam, or bare with `gap` all round."""
        if foam:
            return self.req_len, self.req_dia
        return self.stack + 2 * gap, self.dia + 2 * gap


def any_lens(label, stack):
    """Generic case-1 position: any lens up to A1's diameter whose length with both caps
    (or with adapter + caps) is <= stack."""
    return Config(label, (), 0.0, dia_override=A1.dia, stack_override=stack,
                  short_override=f"UP TO {stack:.0f}")


CASE1_CONFIGS = [
    Config("1: 18-55 + EF cap", (L1,), EF_REAR_CAP),
    any_lens("2: any lens <= 91 mm capped", 91.0),
    Config("3: 18-55 + adapter", (L1, A1), RF_REAR_CAP),
    any_lens("4: any lens <= 115 mm capped", 115.0),
    Config("5: 55-250 + EF cap", (L2,), EF_REAR_CAP),
    # 55-250 + adapter dropped from spec (would need 161.2 mm, leaving only ~18 mm overlap)
]
CASE2_CONFIG = (Config("50 + adapter", (L3, A1), RF_REAR_CAP)
                if CASE2_WITH_ADAPTER else Config("50 + EF cap", (L3,), EF_REAR_CAP))
CASE4_CONFIG = Config("18-55 + EF cap", (L1,), EF_REAR_CAP)
CASE5_CONFIG = Config("55-250 + EF cap", (L2,), EF_REAR_CAP)
CASE6_CONFIG = Config("18-55 + adapter", (L1, A1), RF_REAR_CAP)
CASE3_CONFIG = Config("100-400" + (" + rev. hood" if L4_WITH_HOOD else ""), (L4,), RF_REAR_CAP,
                      HOOD_REVERSED_DIA if L4_WITH_HOOD else None)
