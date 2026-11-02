# Provenance

Built 2026-11-02 by tools/build.py with kicad-cli 10.0.7. Sources, in precedence order:

| key | kind | file | repository commit | packages | symbols | converter warnings |
|---|---|---|---|---|---|---|
| passives | PRIMARY | `Cold-Silicon/bschulz_passives.lbr` | 5823fee 2022-12-15 | 346 | 500 | – |
| bschulz | PRIMARY | `Cold-Silicon/bschulz.lbr` | 5823fee 2022-12-15 | 613 | 987 | Ignoring a rectangle since Eagle layer '200bmp' (200) was not mapped; Ignoring a text since Eagle layer '200bmp' (200) was not mapped; Ignoring a text since Eagle layer 'Milling' (46) was not mapped; Ignoring a wire since Eagle layer 'Milling' (46) was not mapped; Ignoring a wire since Eagle layer 'tCAD' (57) was not mapped; Ignoring a wire since Eagle layer 'vRestrict' (43) was not mapped |
| awickert | PRIMARY | `NorthernWidget-Eagle-Libraries/awickert.lbr` | 197b8f8 2021-03-02 | 38 | 36 | Ignoring a polygon since Eagle layer '200bmp' (200) was not mapped |
| csandell | PRIMARY | `NorthernWidget-Eagle-Libraries/csandell.lbr` | 9c3f077 2017-11-06 | 9 | 8 | – |

Library: **851 footprints** in `nw-cold-silicon.pretty`, **1375 symbols** in `nw-cold-silicon.kicad_sym`.
Second pass of kicad-cli upgrade on the output: 0 footprint files changed, symbol file identical.

Rule: precedence is the order of the table; identical content is kept once; differing content from a PRIMARY source is kept as NAME_key; an EXTRAS source adds only names absent so far. See COLLISIONS.md.
