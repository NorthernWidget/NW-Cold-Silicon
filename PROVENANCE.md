# Provenance

Built 2026-11-02 by tools/build.py with kicad-cli 10.0.7. Sources, in precedence order:

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
| okapi | `Project-Okapi/Hardware/KiCAD-10import/Okapi.kicad_pcb` | 69 | 63 | 2 | 3 | 4 | 2 |
| margay | `Project-Margay/Hardware/KiCAD/Margay.kicad_pcb` | 37 | 34 | 0 | 1 | 1 | 4 |

Added from the boards:

- `PARTICLE_M.2EKEY_NOPROG`: from Bobby's working copy of bschulz, never committed to Cold-Silicon.
- `SD_WURTH_WR-CRD`: full-size SD holder, Würth Elektronik 693063010911 (the package's own datasheet link), drawn by Bobby Schulz; in no committed Eagle library. Adafruit's SDCARD has the same pitch and pad count with 4.0 by 1.2 mm signal pads against 1.0 by 1.5 here, a relative and not the source (Andy, 2026-11-02: Bobby's is the one).
- `SOT23-3@1`: Eagle's name for a second SOT23-3 variant in bschulz; identical on the Okapi and Margay boards.
- `USB_C_CUSB31-CFM2AX-01-X`: USB-C receptacle; Okapi.brd and Margay.brd name Adafruit's microbuilder library, which does not hold it in the 2015 release that is Adafruit's current master.
- `USB_MICRO_VERT_MOLEX`: from Bobby's working copy of bschulz, never committed to Cold-Silicon.

Library: **848 footprints** in `nw-cold-silicon.pretty`, **1403 symbols** in `nw-cold-silicon.kicad_sym`.
Second pass of kicad-cli upgrade on the output: 0 footprint files changed, symbol file identical.

Rule: precedence is the order of the table; identical content is kept once; differing content from a PRIMARY source is kept as NAME_key; an EXTRAS source adds only names absent so far. See COLLISIONS.md.
