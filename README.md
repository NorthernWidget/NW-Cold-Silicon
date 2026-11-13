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

Clone the repository (`git clone https://github.com/NorthernWidget/NW-Cold-Silicon.git`) and add the two libraries to a project's `fp-lib-table` and `sym-lib-table`, or
to the global tables, under the nickname `nw-cold-silicon`. The Northern Widget boards clone it beside their own repositories and point at `${KIPRJMOD}/../../../NW-Cold-Silicon`:

```
(lib (name "nw-cold-silicon") (type "KiCad") (uri "${NW_LIBS}/NW-Cold-Silicon/nw-cold-silicon.pretty") (options "") (descr ""))
(lib (name "nw-cold-silicon") (type "KiCad") (uri "${NW_LIBS}/NW-Cold-Silicon/nw-cold-silicon.kicad_sym") (options "") (descr ""))
```

The nickname must be `nw-cold-silicon`: every symbol's Footprint field names
it. In the project file, set `page_layout_descr_file` under both `schematic`
and `pcbnew` to `${NW_LIBS}/NW-Cold-Silicon/nw-cold-silicon.kicad_wks` and
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

A few footprints are drawn in KiCad rather than converted: they live in `native/`, the build copies them in under their own names, and each names its source in its description. The first is `R0402_0603`, a resistor land that takes an 0603 or an 0402 (the geometry of Blues' MN_0402_0603), for user-swappable parts.

## What the build corrects

KiCad's Eagle reader is the converter, and the output is what it writes, with
these corrections, each a table in `tools/build.py` keyed by symbol or
footprint name and listed in `COLLISIONS.md` with the datasheet or the
fabricated board that justifies it:

- `PIN_TYPES`: a pin's electrical type by its datasheet (the reader types
  every Eagle pwr pin as a power input and every other pin as an input or
  bidirectional, so no rail had a driver and every LED was a supply).
- `PASSIVE`: every pin of a diode, LED, transistor, fuse, switch or connector,
  KiCad's own typing for discretes.
- `PIN_DROP` and `PIN_SPREAD`: pins stacked on one point, which KiCad joins
  by geometry where Eagle kept each pad its own (the micro-USB shell).
- `PAD_RENUMBER`: a shell drawn as pairs of plated holes joined by a copper
  bar, Eagle's one shape; the pair shares a pad number and the bar becomes
  the pad's own primitive.
- `MILLED_SLOTS`: a slot Eagle milled (a stadium on layer 46, Milling)
  around a pad's drill, which KiCad's reader ignores, leaving a round drill
  where the part's stake needs a slot; the pad takes the slot as its oval
  drill (the USB-C and vertical micro-USB shells).
- `FP_ATTRS`: a footprint attribute the part needs (one shared mask opening).
- Eagle's restring: every through-hole pad at least drill + 2 × max(25 % of
  the drill, 5 mil), the ring Eagle fabricates whatever the package drew.
- Eagle's bRestrict: a no-copper keepout on the bottom layer, where the
  reader had written a via-only keepout on every copper layer.
- `PWR_FLAG`, lifted from KiCad's own symbol library, so a board needs no
  second library for it.

Add a line to the table, rebuild, and refresh the sheets that hold the
symbol (`refresh_symbols.py` in NW-Tests/kicad) or re-body the boards
(`rebody.py`). Nothing is edited in a sheet's embedded copy by hand.

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
