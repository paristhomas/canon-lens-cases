# Notes for agents working on this repo

Parametric, FDM-printable lens cases built with build123d. `README.md` is the human-facing
overview; this file is the technical reference.

## Workflow

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv/Scripts/
python build_all.py            # all 19 variants -> out/*.stl, *.step, out/manifest.json (or: build_all.py case2 / case1_threaded)
python verify.py               # must end in RESULT: PASS (non-zero exit otherwise)
python report.py               # out/report.md: fit, volume, print time
python render_gallery.py       # docs/img/gallery/*.png (README images)
python export_bambu.py         # print/bambu/*.3mf (needs Bambu Studio installed; see the script header)
python export_viewer.py        # out/web/ data for viewer/index.html (optional)
python gap_diagram.py          # viewer/clearances.html (optional)
```

After a geometry change that passes `verify.py`, refresh the committed print files:
`cp out/*.stl print/stl/ && cp out/*.step print/step/ && cp out/report.md print/`, then
`export_bambu.py` and `render_gallery.py`, and update the tables below from `out/report.md`.

Rules the geometry follows (checked by `verify.py`): no overhang > 45° in print orientation,
tube walls ≥ 2.0 mm, caps ≥ 4.0 mm, mating gaps ≥ 0.2 mm,
nothing protrudes past the lid diameter. All numbers live in `params.py`, tagged `[SPEC]`
(manufacturer figure), `[EST]` (estimate, measure to confirm) or `[DES]` (design choice).

### Print orientation (`out/`, `print/stl/`)

| File | On the bed |
|---|---|
| `caseN_<style>_body` | floor |
| `caseN_<style>_lid` (fixed cases) | top face (open end up) |
| `case1_<style>_inner` | top face |
| `case1_threaded_ring`, `case1_tpu_ring` | flat |

Styles: `bayonet` and `threaded` (PETG, foam-lined), `tpu` (threaded, TPU, no foam), and on case 1 only `tpu_bayonet` (bayonet, TPU, no foam).

`out/visual/` holds foam and lens models for renders only.

## Assumptions and estimates

| # | Item | Value | Source |
|---|---|---|---|
| 1 | L1 EF-S 18-55 f/4-5.6 IS STM (newer, 2017 version) | Ø66.5 × 61.8 | Canon spec |
| 2 | L2 EF-S 55-250 f/4-5.6 IS STM | Ø70.0 × 113.2 (spec 111.2; about 2 mm longer in use). The foam cases were printed for 111.2 and fit well with 2 mm less end foam, so they keep that length (`Item.foam_less`); the tpu cases get the 2 mm | Canon spec, **measured** |
| 3 | L3 EF 50 f/1.8 STM | Ø69.2 × 39.3 | Canon spec |
| 4 | L4 RF 100-400 F5.6-8 IS USM | Ø79.5 × 164.7 | Canon spec |
| 5 | A1 Mount Adapter EF-EOS R | Ø71.2 × 24.0 | Canon spec |
| 6 | Front cap protrusion | 6 mm; **5 mm on the EF 50** (`Item.front_cap`: the first printed case was ~1 mm long) | **estimate – measure** |
| 7 | EF rear cap | 12 mm | **estimate – measure** |
| 8 | RF rear dust cap (on adapter or L4) | 10 mm | **estimate – measure** |
| 9 | ET-74B hood reversed on L4 | Ø85, no added length, **off** | estimate |
| 10 | Cap diameters (lens models only: EF rear 62, RF rear 66, front = filter + 2) | – | estimate, render only |
| 11 | Foam | 2.25 mm radial (3 mm printed bulky), **8 mm under the rear cap**, 5 mm over the front cap, inside the case. tpu style: no foam, `BARE_GAP` 1 mm all round and at each end | spec |
| 12 | Fit clearance | +1.0 mm on diameter on top of foam | spec |
| 13 | Case 1 "55-250 + adapter" position | **dropped** (it left only 18 mm of telescoping overlap) | decision |
| 14 | Thread form | 45° flanks (90° included), not ISO 30° trapezoid, so internal and external threads print without supports in any orientation | design |
| 15 | Bayonet retention | the J-hook relies on the end foam pushing the lid out by 1.5 mm; the detent bump (0.2 mm interference, printed just right) gives the click | design |
| 16 | Lens models | stepped solids that fill each lens's spec envelope (no Canon CAD is published) – if the model clears, the lens clears | design |
| 17 | Material and print time | PETG 1.27 g/cm³ (TPU 1.21); time = volume ÷ 5 or 12 mm³/s × 1.15, ±30 % | estimate |
| 18 | Case 1 with the 18-55 alone | 4.7 mm of extra diameter (bore is sized for the adapter) – wrap one extra layer of foam. The tpu case 1 has no foam, so this lens has 2.4 mm of radial play | note |
| 19 | Backpack use | no protrusions: the lanyard lug and webbing slot exist but are **off** by default (`LANYARD_LUG`, `WEBBING_SLOT`) | design |
| 21 | Wall / cap minimums | tube walls ≥ **2.0 mm** (`WALL`: thread roots, flute floors, and outside the bayonet J-slot: `BAYONET_OUTER_WALL`); **3.0 mm** on case 1 (body) and on the fixed cases for the two longest lenses, cases 3 and 5 (`WALL_THICK`, `THICK_WALL_CASES`); case 1 top tube **2.5 mm** (`TELE_INNER_WALL`); **4.0 mm** on every tpu tube (`WALL_TPU`), but **2.0 mm** on a tpu lid outside its thread (`WALL_TPU_LID`: 4 mm through the ridges, and a smaller grip). Floors and lid tops **4.0 mm**, because the ends take the drop impacts | design |
| 22 | Print tolerance | every mating gap ≥ **0.2 mm** square to the surfaces, measured on the meshes (0.24–0.40 mm actual). Each was cut by 0.1 mm once after the first print, which was a touch loose: 0.3 mm radial on sliding fits; threads 0.4 mm radial and 0.4 mm axial on the flanks (0.28 mm square to the 45° flank); bayonet pin 0.35 mm axial and 0.3 mm at the tip | design |
| 23 | Interchangeable lids | foam styles: fixed-case bores snap to standard sizes (`BORE_CLASSES` = 77.0, 85.5 mm). Cases 2, 4 and 6 share one lid (`Ø77`, engraved inside on the ceiling) per style; a smaller lens gets a thicker foam sleeve. Case 5 has thicker walls, so its lid is `Ø77/3`, and case 3's is `Ø86/3`. tpu cases fit their lens, so every tpu lid is its own | design |
| 24 | 50 mm case | **no adapter**: EF 50 mm + EF rear cap (`CASE2_WITH_ADAPTER = False`) | design |
| 25 | Thread | 6 mm pitch, 2.0 mm deep, 45° flanks; lids are 2-start (12 mm lead, 9 mm of thread, so 3/4 turn to close), and the 2-start telescoping thread (12 mm lead) about 4 turns between positions | design |
| 26 | Bayonet engagement | slot 2.0 mm deep, so the pin hooks 1.7 mm past the mating wall after clearances; **8 pins** (an entry every 45°), 6 mm wide × 6 mm tall (with 4 pins 4 mm tall, one snapped off when an empty case was dropped), hidden inside the 16 mm lid skirt, so nothing sticks out. Every bayonet locks **clockwise** seen from above, like a jar lid | design |
| 27 | Concave anti-roll cuts | **off** (`CUT_ARCS = 0`, `LOWER_CUTS = 0`): on the print they didn't stop it rolling much and looked poor. The code can still make them | design |
| 28 | Lower body | a plain cylinder at the minimum wall, stepping out to the grip band with a 45° taper. Grip band 10 mm tall on fixed cases (`GRIP_BAND`), 20 mm on case 1 (`TELE_GRIP_BAND`) | design |
| 32 | Bayonet entry | one helical lead-in ramp per entry channel at 30° (`LEAD_IN_ANGLE`), on the side the pin arrives from while turning clockwise to lock; the other side (toward the channel's own lock slot) is vertical. So closing is always push + turn clockwise, from any angle: the pin runs along the rim, down the ramp, stops against the vertical side, drops down the channel and turns into the lock. Ramp length: about 17 mm of the 25 mm between entries on fixed lids (it has to pass under the neighbouring lock slot), the full 25 mm on case 1. The entry triangle (`ENTRY_MARK`) is **off**: with 8 entries and any-angle entry it isn't needed | design |
| 33 | Lens text | lens mount + range, then f-number, bold, at one size (11.5 mm, ~1.5 mm strokes so it prints with a 0.6 mm nozzle): `EF 50 / f/1.8`, `EF-S 18-55 / f/4-5.6 / + ADAPTER` on the base of the fixed cases; `EF-S 18-55 / EF-S 55-250 / f/4-5.6` on the case 1 top. It is the only text on the outside | design |
| 31 | Lock arrow | engraved clockwise arrow from an open padlock to a closed one, on every fixed-case lid and on the case 1 base (mirrored, so it reads clockwise seen from below: the way to turn the body). Fixed lids carry their size code inside | design |
| 29 | Case 1 positions | 5: the three lens positions plus two generic ones (104 and 128 mm interior) for **any lens up to Ø71.2 whose length with caps (or with adapter + caps) is ≤ 91 / ≤ 115 mm** | design |
| 30 | STL resolution | 0.008 mm chord sag, 0.05 rad angular step (~1.8 mm facets around a 95 mm case); about 120 MB in total | design |
| 20 | Fillets vs printability | edges on the print bed get a 2 mm 45° chamfer with an R3 fillet above it (a true fillet there would overhang); all other outside edges are R1.5 | design |
| 34 | Case 1 tpu_bayonet | TPU, no foam, 0.5 mm lens gap all round and at each end (`TPU_BAYONET_GAP`), 4.5 mm tube walls (`TPU_BAYONET_WALL`), 5 mm floor and top (`TPU_BAYONET_END`). Bayonet features 1.5× for the soft material (`TPU_BAYONET_SCALE`): pins 9 mm wide, groove 3 mm deep with 3.5 mm of wall outside it, hook notch 2.25 mm, detent bump R1.5 with 0.3 mm interference. Pin height stays 6 mm, because 9 mm legs would merge between positions 11 mm apart. Gaps 0.1 mm looser (`TPU_EXTRA_CLEAR`): slide 0.4, pin radial 0.4, pin axial 0.45. With no foam nothing pushes the pin into the hook notch: by design the bigger detent bump holds the position | design |

All numbers live in `params.py`, tagged `[SPEC]`, `[EST]` or `[DES]`.

---

## Changing parameters

Edit `params.py` and re-run `build_all.py` → `verify.py`. The verifier fails loudly if anything no longer fits.

- **Re-measured caps:** `FRONT_CAP`, `EF_REAR_CAP`, `RF_REAR_CAP`. Measure how far each cap sticks out beyond the lens length in the spec table, i.e. front cap beyond the filter rim and rear cap beyond the mount flange. Every case length follows automatically.
- **Foam / clearance:** `FOAM_RADIAL`, `FOAM_END_BOTTOM`, `FOAM_END_TOP`, `FIT_CLEAR_DIA`; tpu style `BARE_GAP`, `WALL_TPU`.
- **Printer tuning:** `SLIDE_CLEAR` (0.3 mm radial), `PIN_RADIAL_GAP` (0.3) and `PIN_AXIAL_CLEAR` (0.35) for the bayonet, `THREAD_CLEAR` (0.4) and `THREAD_FLANK_GAP` (0.4) for threads. Keep `DETENT_BUMP_H` − `PIN_RADIAL_GAP` at 0.2 (the click). `MIN_PRINT_GAP` (0.2) is what `verify.py` enforces. If the test lid is tight, raise them by 0.05–0.1.
- **Bayonet wall:** `BAYONET_OUTER_WALL` (2.0) is the wall outside the J-slot; each extra 1 mm adds 2 mm to the case Ø.
- **Cuts and lock arrow:** `CUT_ARCS`, `CUT_ANGLE0`, `CUT_CHORD`, `CUT_DEPTH`, `LOWER_CUTS` (all off); `LOCK_ARROW` (on/off).
- **Bayonet entry:** `ENTRY_MARK` (on/off), `ENTRY_MARK_W`, `ENTRY_MARK_H`, `ENTRY_MARK_DEPTH`; `LEAD_IN_ANGLE`, `LEAD_IN_LAND`.
- **Grip:** `GRIP_FLUTES`, `FLUTE_DEPTH`, `FLUTE_W`, `GRIP_BAND`, `TELE_GRIP_BAND` (the body's flush grip band). Edges: `EDGE_CHAMFER`, `BED_FILLET`, `EDGE_FILLET`.
- **Options:** `LANYARD_LUG` (off – it protrudes 8 mm), `L4_WITH_HOOD` (case 3 bore → Ø92), `CASE2_WITH_ADAPTER` (False → 50 mm + EF cap only, 22 mm shorter), `WEBBING_SLOT` with `WEBBING_MODE = "belt" | "molle"`, `DESICCANT_POCKET` (Ø30 × 6 mm in the body floor; adds 6 mm length).
- **TPU bayonet (case 1):** `TPU_BAYONET_SCALE`, `TPU_EXTRA_CLEAR`.
- **Joint feel:** `BAYONET_PINS`, `PIN_HEIGHT`, `LID_ENGAGE`, `BAYONET_TWIST_DEG`, `BAYONET_NOTCH`, `DETENT_BUMP_H` (click strength), `THREAD_ENGAGE`, `THREAD_STARTS`, `TELE_THREAD_STARTS`.
- **Telescoping set:** edit `CASE1_CONFIGS` (any number of configurations; `any_lens(label, stack)` adds a generic one). Keep positions ≥ 10 mm apart so a solid land stays between the J-legs. Each one gets its own twist-lock position (bayonet) or index mark (threaded).

### A fixed case for another lens

```sh
python make_case.py --name ef35 --dia 77.9 --length 62.6 --rear-cap 12 --label "EF 35 f/2|IS USM"
```

`--dia`/`--length` are the lens spec without caps; front cap, foam and clearances come from `params.py`.

---

## Fit table (measured on the exported meshes)

Required = lens stack + caps + foam + clearance (tpu: lens stack + caps + 1 mm all round). "Measured" is ray-cast on the assembled STLs in each position.

| Variant | Configuration | Required L × Ø | Measured interior L × Ø | Length margin | Ø margin |
|---|---|---|---|---|---|
| case1_bayonet | 1: 18-55 + EF cap | 92.8 × 72.0 | 93.00 × 76.99 | +0.20 | +4.99 |
| case1_bayonet | 2: any lens <= 91 mm capped | 104.0 × 76.7 | 104.00 × 76.99 | +0.00 | +0.29 |
| case1_bayonet | 3: 18-55 + adapter | 114.8 × 76.7 | 115.00 × 76.99 | +0.20 | +0.29 |
| case1_bayonet | 4: any lens <= 115 mm capped | 128.0 × 76.7 | 128.00 × 76.99 | +0.00 | +0.29 |
| case1_bayonet | 5: 55-250 + EF cap | 142.2 × 75.5 | 142.50 × 76.99 | +0.30 | +1.49 |
| case1_threaded | 1: 18-55 + EF cap | 92.8 × 72.0 | 93.00 × 76.99 | +0.20 | +4.99 |
| case1_threaded | 2: any lens <= 91 mm capped | 104.0 × 76.7 | 104.00 × 76.99 | +0.00 | +0.29 |
| case1_threaded | 3: 18-55 + adapter | 114.8 × 76.7 | 115.00 × 76.99 | +0.20 | +0.29 |
| case1_threaded | 4: any lens <= 115 mm capped | 128.0 × 76.7 | 128.00 × 76.99 | +0.00 | +0.29 |
| case1_threaded | 5: 55-250 + EF cap | 142.2 × 75.5 | 142.50 × 76.99 | +0.30 | +1.49 |
| case1_tpu | 1: 18-55 + EF cap | 81.8 × 68.5 | 82.00 × 73.39 | +0.20 | +4.89 |
| case1_tpu | 2: any lens <= 91 mm capped | 93.0 × 73.2 | 93.00 × 73.39 | +0.00 | +0.19 |
| case1_tpu | 3: 18-55 + adapter | 103.8 × 73.2 | 104.00 × 73.39 | +0.20 | +0.19 |
| case1_tpu | 4: any lens <= 115 mm capped | 117.0 × 73.2 | 117.00 × 73.39 | +0.00 | +0.19 |
| case1_tpu | 5: 55-250 + EF cap | 133.2 × 72.0 | 133.50 × 73.39 | +0.30 | +1.39 |
| case1_tpu_bayonet | 1: 18-55 + EF cap | 80.8 × 67.5 | 81.00 × 72.39 | +0.20 | +4.89 |
| case1_tpu_bayonet | 2: any lens <= 91 mm capped | 92.0 × 72.2 | 92.00 × 72.39 | +0.00 | +0.19 |
| case1_tpu_bayonet | 3: 18-55 + adapter | 102.8 × 72.2 | 103.00 × 72.39 | +0.20 | +0.19 |
| case1_tpu_bayonet | 4: any lens <= 115 mm capped | 116.0 × 72.2 | 116.00 × 72.39 | +0.00 | +0.19 |
| case1_tpu_bayonet | 5: 55-250 + EF cap | 132.2 × 71.0 | 132.50 × 72.39 | +0.30 | +1.39 |
| case2_bayonet | 50 + EF cap | 69.3 × 74.7 | 69.50 × 76.99 | +0.20 | +2.29 |
| case2_threaded | 50 + EF cap | 69.3 × 74.7 | 69.50 × 76.99 | +0.20 | +2.29 |
| case2_tpu | 50 + EF cap | 58.3 × 71.2 | 58.50 × 71.39 | +0.20 | +0.19 |
| case3_bayonet | 100-400 | 193.7 × 85.0 | 194.00 × 85.49 | +0.30 | +0.49 |
| case3_threaded | 100-400 | 193.7 × 85.0 | 194.00 × 85.49 | +0.30 | +0.49 |
| case3_tpu | 100-400 | 182.7 × 81.5 | 183.00 × 81.69 | +0.30 | +0.19 |
| case4_bayonet | 18-55 + EF cap | 92.8 × 72.0 | 93.00 × 76.99 | +0.20 | +4.99 |
| case4_threaded | 18-55 + EF cap | 92.8 × 72.0 | 93.00 × 76.99 | +0.20 | +4.99 |
| case4_tpu | 18-55 + EF cap | 81.8 × 68.5 | 82.00 × 68.69 | +0.20 | +0.19 |
| case5_bayonet | 55-250 + EF cap | 142.2 × 75.5 | 142.50 × 76.99 | +0.30 | +1.49 |
| case5_threaded | 55-250 + EF cap | 142.2 × 75.5 | 142.50 × 76.99 | +0.30 | +1.49 |
| case5_tpu | 55-250 + EF cap | 133.2 × 72.0 | 133.50 × 72.19 | +0.30 | +0.19 |
| case6_bayonet | 18-55 + adapter | 114.8 × 76.7 | 115.00 × 76.99 | +0.20 | +0.29 |
| case6_threaded | 18-55 + adapter | 114.8 × 76.7 | 115.00 × 76.99 | +0.20 | +0.29 |
| case6_tpu | 18-55 + adapter | 103.8 × 73.2 | 104.00 × 73.39 | +0.20 | +0.19 |

Diameter margins above about 0.3 mm in the foam styles are the shared standard bore; the extra is taken up by a thicker foam sleeve.

The case 1 travel check passes: every position is ≥ its requirement and ≤ requirement + 3 mm, so the lens won't rattle. Telescoping overlap at full extension is 36.6 mm for bayonet, 31.1 mm for threaded and 18.1 mm for tpu and 22.1 mm for tpu_bayonet (11 mm shorter, with no end foam), against a body ID of about 82 mm.

### External size

Nothing protrudes beyond this envelope. The flutes are recessed, and the lid and grip band share the maximum diameter.

| Variant | Max outer Ø | 92.2 | 94.4 | 95.8 | 91.2 | 91.4 | 89.8 | 101.7 | 103.9 | 100.1 | 91.2 | 91.4 | 87.1 | 93.2 | 95.4 | 90.6 | 91.2 | 91.4 | 91.8 |
|---|---|---|
| case1 bayonet | 92.2 | 102.2 → 151.7 |
| case1 threaded | 94.4 | 102.2 → 151.7 |
| case1 tpu | 95.8 | 91.2 → 142.7 |
| case1 tpu_bayonet | 96.8 | 92.2 → 143.7 |
| case2 bayonet | 91.2 | 78.7 |
| case2 threaded | 91.4 | 78.7 |
| case2 tpu | 89.8 | 67.7 |
| case3 bayonet | 101.7 | 203.2 |
| case3 threaded | 103.9 | 203.2 |
| case3 tpu | 100.1 | 192.2 |
| case4 bayonet | 91.2 | 102.2 |
| case4 threaded | 91.4 | 102.2 |
| case4 tpu | 87.1 | 91.2 |
| case5 bayonet | 93.2 | 151.7 |
| case5 threaded | 95.4 | 151.7 |
| case5 tpu | 90.6 | 142.7 |
| case6 bayonet | 91.2 | 124.2 |
| case6 threaded | 91.4 | 124.2 |
| case6 tpu | 91.8 | 113.2 |

The optional lanyard lug adds 8 mm on one side, and the optional webbing slot 7 mm (4 mm slot + 3 mm bar).

---

## How it works

**Fixed case.** The body is a cup with a 4.6 mm floor (4 mm + 0.6 mm engraving). The lid's skirt overlaps the body's top 14.5 mm on the bayonet and about 16 mm on the threaded version.
- **Bayonet:** eight pins near the body rim. Their underside is a 45° wedge so they print unsupported. A ramp in the lid leads each into an axial channel; they twist 25° clockwise past a detent bump, and the foam pushes them up 1.5 mm into a hook notch. That locks the lid against both axial and rotational movement. To open: push, twist back, lift.
- **Threaded:** 6 mm pitch, 2.0 mm deep 2-start thread with 45° flanks, closing in 3/4 turn. The lid ceiling seats on the body rim. The tpu style is the same with 4 mm walls and no foam.

**Telescoping case (case 1).** A body with a closed floor, plus a top tube with a closed top and an 8 mm fluted grip flange that slides inside it.
- **Bayonet:** the body wall carries a J-track, a groove 2.0 mm deep in a 4.0 mm wall (2 mm remains), with one axial channel per pin (8) and one twist leg + hook notch + detent per configuration (5 of them). Pull the tube up, twist into the leg for the lens you're packing, and release. It clicks and stays put under hand pressure. The tube can only move again if it is pushed in 1.5 mm *and* twisted back.
- **Threaded:** a full-length 2-start thread (lead 8 mm, about 6 turns from position 1 to 3) and a lock ring that jams on the body rim. Index marks are V-notches across the thread crests where the ring's top edge sits, coded with 1, 2 or 3 dashes. Position k has k dashes, shortest first. The thread adjusts continuously; the ring makes it rigid.

**Common features:**
- **Flush outline:** the lid's outer wall is 0.8 mm thicker than the minimum. A grip band at the top of the body (10 mm on fixed cases, 20 mm on case 1) is flush with the lid, then steps in to the body with a filleted 45° taper. The taper is the band's underside, so it prints without supports.
- **Recessed grip:** 56 vertical flutes, R2 and 0.8 mm deep, cut into the lid, the body band, the top-tube flange and the ring. They run straight out through both ends (on the case 1 body, half way down the band's taper), and the wall under every flute is still at the minimum.
- **Bayonet use:** to close, set the lid / top tube on at any angle, push and turn clockwise until it clicks. To open: push, turn anticlockwise, lift.
- **Lock arrow:** a clockwise arrow from an open padlock to a closed one (fixed lids; case 1 base).
- **Rounded edges:** R1.5 fillets on outside edges. Bed-side edges get a 2 mm chamfer with an R3 fillet above it.
- **Labels:** the lens details (mount + range, f-number) are engraved on the body base (case 1: on the top), bold 11.5 mm on every case (`LABEL_FONT_BASE`, `Item.base`). Fixed-case lids carry only a size code (`Ø77`, `Ø77/3`, `Ø86/3`; tpu: the bore), engraved inside on the ceiling, so a lid fits any body of that size. Case 1 positions click in shortest first; there is no legend.
- **Optional, off by default:** a lanyard lug with a 45° diamond cord hole, a webbing slot, and a desiccant pocket.

---

## Styles: A bayonet, B threaded, C tpu

From `report.py`, which computes volume from the solids and print time without a slicer (C in TPU, 1.21 g/cm³):

| | Case 1 A | Case 1 B | Case 1 C | Case 2 A | Case 2 B | Case 2 C | Case 3 A | Case 3 B | Case 3 C | Case 4 A | Case 4 B | Case 4 C | Case 5 A | Case 5 B | Case 5 C | Case 6 A | Case 6 B | Case 6 C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Printed parts | 2 | 3 (+ring) | 3 (+ring) | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| Volume cm³ / g | 197 / 250 | 246 / 313 | 278 / 336 | 117 / 148 | 119 / 151 | 137 / 166 | 261 / 332 | 276 / 350 | 296 / 358 | 128 / 163 | 130 / 165 | 152 / 184 | 193 / 245 | 206 / 261 | 209 / 253 | 139 / 177 | 141 / 179 | 186 / 225 |
| Print time @5 / @12 mm³/s | 12h34 / 5h14 | 15h44 / 6h33 | 17h45 / 7h24 | 7h28 / 3h07 | 7h35 / 3h09 | 8h45 / 3h39 | 16h42 / 6h58 | 17h37 / 7h20 | 18h54 / 7h53 | 8h13 / 3h25 | 8h19 / 3h28 | 9h43 / 4h03 | 12h18 / 5h08 | 13h09 / 5h29 | 13h20 / 5h33 | 8h54 / 3h42 | 9h01 / 3h45 | 11h52 / 4h57 |
| Max outer Ø | 91.2 | 91.4 | 95.8 | 91.2 | 91.4 | 93.8 | 101.7 | 103.9 | 104.1 | 91.2 | 91.4 | 91.1 | 93.2 | 95.4 | 94.6 | 91.2 | 91.4 | 95.8 |

| | A – Bayonet | B – Threaded |
|---|---|---|
| **Ease of use** | Push, twist clockwise, click, from any angle: easy with gloves or wet hands. Case 1 positions are discrete and can't be set wrong. | Lids take 3/4 turn. Case 1 takes about 4 turns between positions, plus setting the lock ring and reading the marks. |
| **Positive lock** | Hook notch + foam preload + detent bump: won't open in a pack. | Friction only on lids (they can back off under vibration). Case 1 is locked rigidly by the jam ring. |
| **Robustness** | Pins (8 × 6 × 6 mm) are the weak point if the case is dropped lid-first (4 mm tall pins broke). Detent bumps wear after many cycles, but the hook still holds. Grit can collect in the grooves. | Threads spread load over the whole circumference and tolerate dropping, and grit is easier to clear. More sensitive to printer over-extrusion. |
| **Dust / splash** | Lid sits 1.5 mm off the rim (foam closes it). Not sealed. | Lid ceiling seats on the rim: better dust seal. Neither is waterproof. |
| **Adjustability (case 1)** | Only the designed lengths. | Any length in the range. |
| **In a backpack** | When extended, the top tube is smooth. | When extended, the external thread is exposed and collects grit and fluff. |
| **Size** | about the same Ø | about the same Ø |

**Recommendation for backpack use: bayonet for all three.**
- It is positively locked, so it can't unscrew in a bag.
- It opens with one push-twist.
- When extended, the telescoping case has no exposed thread.

Choose the threaded case 1 only if you want arbitrary lengths for future lenses. The tpu style is the threaded
design printed in flexible TPU with no foam (untested).

---

## Verification

`verify.py` reads only the exported STLs (via `out/manifest.json`) and fails with a non-zero exit code on any problem:

1. **Fit table:** interior length and diameter, ray-cast on the assembled meshes in every configuration.
2. **Telescoping travel:** each position is ≥ its requirement and ≤ requirement + 3 mm.
3. **Watertight / manifold:** trimesh and manifold3d checks on every STL.
4. **Overhangs > 45°:** checked in print orientation. Engraved-label bridges on the bed face are reported separately.
5. **Walls:** radial walls ≥ 2.0 mm (also ≥ `BAYONET_OUTER_WALL` outside a bayonet J-slot: rays whose wall starts > 1 mm beyond the bore, on the parts flagged `groove_wall` in the manifest) and caps ≥ 4.0 mm, less the STL facet sag.
6. **Interference:** parts must not overlap in any configuration (threads interleave, pins sit in their notches). In a sanity test, rotating a part out of position produced 6 184 mm³ of overlap, so the check does detect collisions.
7. **Lens clearance:** the lens/cap/adapter models must not touch any printed part.
8. **Print gap:** the smallest gap between mating parts in every position must be ≥ 0.2 mm. Flat seating stops, and the lock ring sitting on the body, are excluded because they're meant to touch. `gap_diagram.py` draws these gaps on magnified sections.

Current result: **PASS** on all 19 variants. All 40 STLs are watertight and total about 120 MB. The CAD is exported at 0.008 mm chord sag and a 0.05 rad angular step (`STL_TOL` in `build_all.py`), which gives a smooth outer finish. The lock ring is exported finer still.
- The only overhang outside the labels is about 0.1 mm² (one facet on the case 1 threaded top tube) and 0.01 mm² on the ring top.
- Walls measure 1.996–2.00 mm (2.5 / 3.0 / 4.0 where thicker). The CAD is exact; the difference is the facet sag. Each wall ray is cast twice, 0.07 mm apart, so a ray skimming a lead-in ramp at exactly its height isn't read as a thin wall.
- Caps measure 4.00 mm.
- Mating gaps measure 0.28 mm (threads) and 0.24 mm (bayonet) at the closest.
- The lens models clear the case walls by the foam space (bayonet, threaded) or 1 mm (tpu).

Renders: `render.py` (engineering views -> `out/renders/`), `render_gallery.py` (README images -> `docs/img/gallery/`).

---

## Code layout

```
params.py        all dimensions ([SPEC] / [EST] / [DES])
geometry/        prims (revolve helpers, cup profile), thread, bayonet (pins, J-slot, detent),
                 features (grip flutes, lanyard, webbing, label, desiccant), contents (foam + lens models)
cases.py         fixed_case(), telescoping_case(), all_variants()
build_all.py     STEP + STL export (print orientation) + out/manifest.json
export_viewer.py decimated meshes + models.json for the web viewer (viewer/index.html)
gap_diagram.py   magnified joint sections with measured gaps (viewer/clearances.html)
make_case.py     fixed case for any lens from the command line
verify.py        checks 1–8
render.py        section / iso / exploded / cutaway / contents PNGs (pyvista, matplotlib fallback)
report.py        out/report.md tables
render_gallery.py README images (docs/img/gallery/)
export_bambu.py  Bambu Studio projects (print/bambu/), via the Bambu Studio command line
tests/           fake-geometry fixtures used to prove verify.py catches planted faults
```

## Known limitations

- Detent click force and lid feel are untested on a real print. Expect to tune `DETENT_BUMP_H` and the clearances after the first print.
- The hook-notch retention needs the end foam to be compressed by at least 1.5 mm. With very soft or missing foam the lid is still held by the detent, but more loosely.
- No seal or O-ring: the cases are dust- and knock-resistant, not waterproof.
- Engraved labels on the bed face print as short bridges. They're fine on any tuned printer, but are the one exception to the overhang rule.
