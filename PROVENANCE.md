# Provenance

Built 2026-11-04 by tools/build.py with kicad-cli 10.0.8. Sources, in precedence order:

| key | kind | file | repository commit | packages | symbols | converter warnings |
|---|---|---|---|---|---|---|
| passives | PRIMARY | `Cold-Silicon/bschulz_passives.lbr` | 5823fee 2022-12-15 | 346 | 500 | – |
| bschulz | PRIMARY | `Cold-Silicon/bschulz.lbr` | 5823fee 2022-12-15 | 613 | 987 | Ignoring a rectangle since Eagle layer '200bmp' (200) was not mapped; Ignoring a text since Eagle layer '200bmp' (200) was not mapped; Ignoring a text since Eagle layer 'Milling' (46) was not mapped; Ignoring a wire since Eagle layer 'Milling' (46) was not mapped; Ignoring a wire since Eagle layer 'tCAD' (57) was not mapped; Ignoring a wire since Eagle layer 'vRestrict' (43) was not mapped |
| awickert | PRIMARY | `NorthernWidget-Eagle-Libraries/awickert.lbr` | 197b8f8 2021-03-02 | 38 | 36 | Ignoring a polygon since Eagle layer '200bmp' (200) was not mapped |
| csandell | PRIMARY | `NorthernWidget-Eagle-Libraries/csandell.lbr` | 9c3f077 2017-11-06 | 9 | 8 | – |
| fork | EXTRAS | `Cold-Silicon-awickert/bschulz.lbr` | 1228533 2019-01-18 | 385 | 541 | Ignoring a rectangle since Eagle layer '200bmp' (200) was not mapped; Ignoring a text since Eagle layer '200bmp' (200) was not mapped; Ignoring a wire since Eagle layer 'Milling' (46) was not mapped; Ignoring a wire since Eagle layer 'tCAD' (57) was not mapped |
| old | EXTRAS | `Cold-Silicon/bschulz_Old.lbr` | 3085f18 2017-10-10 | 242 | 273 | Ignoring a rectangle since Eagle layer '200bmp' (200) was not mapped; Ignoring a text since Eagle layer '200bmp' (200) was not mapped; Ignoring a wire since Eagle layer 'Milling' (46) was not mapped |

## Boards

Footprints embedded in the KiCad boards, each matched to the library through its element's Eagle library of origin. A name no source library holds is added from the Eagle board's own package definition through `kicad-cli pcb import`, the converter that built the rest. Columns: identical to the library copy in pads and graphics; same pads but the KiCad board's copy (a June 2026 import) draws the graphics or sizes a non-plated hole differently; pads differ (the board copy is NOT taken over; COLLISIONS.md lists it); unchecked means the board has no front-side instance to compare.

| board | file | embedded names | identical | pads identical | pads differ | added | unchecked |
|---|---|---|---|---|---|---|---|
| okapi | `Project-Okapi/Hardware/KiCAD-10import/Okapi.kicad_pcb` | 68 | 67 | 0 | 0 | 3 | 2 |
| margay | `Project-Margay/Hardware/KiCAD/Margay.kicad_pcb` | 36 | 34 | 0 | 0 | 1 | 4 |

Added from the boards (graphics the importer put on the Rescue layer, from Eagle layers it does not map, are dropped: 42 items; a non-plated hole's pad, which that importer makes 0.254 mm wider than the drill, is set to the drill as the library converter and Eagle have it: 17 pads):

- `4_40_CLOSE`: no note
- `LINX_BAT-HLD-012-SMT`: no note
- `PARTICLE_M.2EKEY_NOPROG`: from Bobby's working copy of bschulz, never committed to Cold-Silicon.
- `SD_WURTH_WR-CRD`: full-size SD holder, Würth Elektronik 693063010911 (the package's own datasheet link), drawn by Bobby Schulz; in no committed Eagle library. Adafruit's SDCARD has the same pitch and pad count with 4.0 by 1.2 mm signal pads against 1.0 by 1.5 here, a relative and not the source (Andy, 2026-11-02: Bobby's is the one).
- `USB_C_CUSB31-CFM2AX-01-X`: USB-C receptacle; Okapi.brd and Margay.brd name Adafruit's microbuilder library, which does not hold it in the 2015 release that is Adafruit's current master.
- `USB_MICRO_VERT_MOLEX`: from Bobby's working copy of bschulz, never committed to Cold-Silicon.

Artwork (logos, 25 footprints and symbols): reference LOGO, excluded from the BOM, the position files and simulation, with a description.
Eagle bRestrict zones (6): the converter had written a via-only keepout on every copper layer; each is a no-copper keepout on B.Cu, as its tRestrict zones are on F.Cu.
No footprint carries a per-pad solder-mask or paste margin (7608 removed): the converter had written KiCad's 4 mil default where Eagle's design rules on every Northern Widget board set a 2.5 mil stop frame, and in KiCad that is the board's pad-to-mask clearance, not the footprint's.
Library: **847 footprints** in `nw-cold-silicon.pretty`, **1402 symbols** in `nw-cold-silicon.kicad_sym`.
Second pass of kicad-cli upgrade on the output: 0 footprint files changed, symbol file identical.

Rule: precedence is the order of the table; identical content is kept once; differing content from a PRIMARY source is kept as NAME_key; an EXTRAS source adds only names absent so far. See COLLISIONS.md.
