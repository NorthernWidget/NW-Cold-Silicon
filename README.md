# nw-cold-silicon

The Northern Widget KiCad library: one footprint library and one symbol
library, built from the Eagle libraries that every Northern Widget board was
drawn with.

- `nw-cold-silicon.pretty/`: the footprints.
- `nw-cold-silicon.kicad_sym`: the symbols, one per Eagle device (a deviceset
  with a package), each pointing at its footprint here.
- `nw-cold-silicon.kicad_wks`: the drawing sheet (border, zones and title
  block) for every schematic page and board. The title block is Bobby's Eagle
  FRAME_A_L, which the Eagle designs placed as a symbol on each sheet: Project
  and Designer come from the project's text variables `PROJECT` and
  `DESIGNER`, REV and Date from each sheet's title block, TITLE is the sheet's
  name in the hierarchy, and the CC BY-SA 4.0 line is printed on every page.
  Point both page-layout settings of a project (schematic and board) at it.
- `PROVENANCE.md`: which Eagle libraries, at which commit, with which
  converter, and the counts. Written by the build, not by hand.
- `COLLISIONS.md`: every name that two sources both held, and what was done.
- `tools/build.py`: the build. Rerun it after a source library changes.

## Use it

Add the two libraries to a project's `fp-lib-table` and `sym-lib-table`, or
to the global tables, under the nickname `nw-cold-silicon`:

```
(lib (name "nw-cold-silicon") (type "KiCad") (uri "${NW_LIBS}/nw-cold-silicon/nw-cold-silicon.pretty") (options "") (descr ""))
(lib (name "nw-cold-silicon") (type "KiCad") (uri "${NW_LIBS}/nw-cold-silicon/nw-cold-silicon.kicad_sym") (options "") (descr ""))
```

The nickname must be `nw-cold-silicon`: every symbol's Footprint field names
it. In the project file, set `page_layout_descr_file` under both `schematic`
and `pcbnew` to `${NW_LIBS}/nw-cold-silicon/nw-cold-silicon.kicad_wks` and
give `text_variables` a `PROJECT` and a `DESIGNER`.

## Where it comes from

The sources are Bobby Schulz's `bschulz.lbr` and `bschulz_passives.lbr`
(Cold-Silicon), `awickert.lbr` and `csandell.lbr` (NorthernWidget-Eagle-
Libraries), plus the devices that exist only in the 2019 Cold-Silicon fork and
in `bschulz_Old.lbr`. KiCad's own Eagle reader did the conversion
(`kicad-cli fp upgrade -o` and `kicad-cli sym upgrade -o`, KiCad 10.0.7), and
the output is what KiCad writes back unchanged. The precedence when two
sources hold one name, and the suffix a losing copy carries, are stated at the
top of `COLLISIONS.md`.

Packages that a built board carries but no Eagle library ever received are
added from the Eagle board file's own package definition, through
`kicad-cli pcb import`, the same converter; `PROVENANCE.md` names the board
and says how the KiCad board's copy compares.

## Rebuild

```sh
python3 tools/build.py            # all sources
python3 tools/build.py --upto bschulz
```

The build fails if KiCad will not load its own output, and it reports whether a
second pass of `kicad-cli` changes anything (it must not).

## License

CC-BY-SA-4.0, the license of Cold-Silicon and of NorthernWidget-Eagle-Libraries
that this library is derived from. Attribution: R. C. Schulz (Cold Silicon),
Andrew D. Wickert and Chad Sandell (NorthernWidget-Eagle-Libraries). The
`LICENSE` text here is the one in NorthernWidget-Eagle-Libraries. Cold-Silicon's
`LICENSE.md` says CC BY-SA 4.0 and its `CC-BY-SA-4.0.txt` holds the
NonCommercial variant's text: the short notice is taken as the license, and
the mismatch is Bobby's to settle.
