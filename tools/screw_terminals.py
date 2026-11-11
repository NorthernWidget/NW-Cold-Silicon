"""Write native/1X<NN>_SCREW_2.54_D1.1.kicad_mod: 2.54 mm rising-clamp terminal blocks on 1.1 mm holes.

One land pattern for two pin sizes (Andy, 2026-11-11): On Shore OSTVN (and the same design sold as
Amphenol Anytek VN and GCT TBC05), pin 0.90 x 0.40 mm, and Phoenix Contact MPT 0,5, pin 0.9 x 0.5 mm.
A flat pin passes a round hole on its diagonal: 0.985 mm (On Shore) and 1.030 mm nominal, 1.098 mm at
maximum tolerance (Phoenix); 1.1 mm is Phoenix's recommended hole. The pads, silkscreen and pin row are
those of 1X<NN>_SCREW, the footprint on the built boards, which had 1.016 mm holes.

Body envelope covers both makers: On Shore 6.5 mm deep with the pin row 3.3 mm from the wire-entry face,
length N x 2.54 + 0.4; Phoenix 6.2 mm deep, centered, length N x 2.54 + 0.46. Sources:
NW-Status studies/sourcing-brands/2026-11-11-screw-terminals-{onshore,phoenix}-agent-report.md.

Run from the repository root, then rerun tools/build.py.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRILL = 1.1
PAD = 1.524
PITCH = 2.54
Y_ENTRY = -3.3   # wire-entry face (On Shore 3.3 mm from the pin row; the silkscreen band marks it)
Y_BACK = 3.2
CRT = 0.25
PHOENIX_ORDER = {6: '1725698', 10: '1725737'}


def f(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def line(x0, y0, x1, y1, layer, w):
    return ('\t(fp_line\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n\t\t)\n'
            '\t\t(layer "%s")\n\t\t(uuid "00000000-0000-0000-0000-000000000000")\n\t)\n') % (f(x0), f(y0), f(x1), f(y1), f(w), layer)


def rect(x0, y0, x1, y1, layer, w):
    return ('\t(fp_rect\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n\t\t)\n'
            '\t\t(fill no)\n\t\t(layer "%s")\n\t\t(uuid "00000000-0000-0000-0000-000000000000")\n\t)\n') % (f(x0), f(y0), f(x1), f(y1), f(w), layer)


def prop(name, value, x, y, layer, hide=False, size=0.8):
    return ('\t(property "%s" "%s"\n\t\t(at %s %s 0)\n\t\t(layer "%s")\n%s\t\t(uuid "00000000-0000-0000-0000-000000000000")\n'
            '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %s %s)\n\t\t\t\t(thickness 0.12)\n\t\t\t)\n\t\t)\n\t)\n') % (
        name, value, f(x), f(y), layer, '\t\t(hide yes)\n' if hide else '', f(size), f(size))


def descr(n):
    px = 'Phoenix Contact MPT 0,5/%d-2,54' % n
    if n in PHOENIX_ORDER:
        px += ' (%s)' % PHOENIX_ORDER[n]
    return ('%d-position 2.54 mm rising-clamp screw terminal on 1.1 mm holes, made to fit both On Shore and Phoenix '
            '(Andy, 2026-11-11). Fits: On Shore OSTVN%02dA150; Amphenol Anytek VN%02dA1500000G (the original of '
            'the On Shore design); GCT TBC05-%02d-1-G-G; %s. Pins: On Shore/Anytek/GCT 0.90 x 0.40 mm, '
            'Phoenix 0.9 x 0.5 mm; 1.1 mm is Phoenix\'s recommended hole. Pads, silkscreen and pin row as '
            '1X%02d_SCREW (1.016 mm holes, On Shore only). Wire entry at -y. Body envelope: On Shore 6.5 mm '
            'deep (pin row 3.3 mm from the entry face), Phoenix 6.2 mm centered.') % (n, n, n, n, px, n)


def footprint(n):
    name = '1X%02d_SCREW_2.54_D1.1' % n
    xs = [(i - (n - 1) / 2) * PITCH for i in range(n)]
    hx = n * PITCH / 2 + 0.23          # silkscreen, as 1X<NN>_SCREW
    bx = (n * PITCH + 0.46) / 2        # longer body (Phoenix)
    t = '(footprint "%s"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n' % name
    t += '\t(descr "%s")\n' % descr(n)
    t += '\t(tags "terminal block screw 2.54 rising clamp On Shore OSTVN Anytek VN GCT TBC05 Phoenix MPT")\n'
    t += prop('Reference', 'REF**', -hx, Y_ENTRY - 1.0, 'F.SilkS')
    t += prop('Value', name, 0, Y_BACK + 1.2, 'F.Fab')
    t += prop('Datasheet', 'https://www.on-shore.com/wp-content/uploads/OSTVNXXA150.pdf', 0, 0, 'F.Fab', hide=True, size=1.27)
    t += prop('Description', '', 0, 0, 'F.Fab', hide=True, size=1.27)
    t += '\t(attr through_hole)\n\t(duplicate_pad_numbers_are_jumpers no)\n'
    w = 0.254
    t += line(-hx, Y_ENTRY, hx, Y_ENTRY, 'F.SilkS', w)
    t += line(-hx, -2.54, hx, -2.54, 'F.SilkS', w)
    t += line(-hx, Y_ENTRY, -hx, Y_BACK, 'F.SilkS', w)
    t += line(hx, Y_ENTRY, hx, Y_BACK, 'F.SilkS', w)
    t += line(-hx, Y_BACK, hx, Y_BACK, 'F.SilkS', w)
    t += rect(-bx, Y_ENTRY, bx, Y_BACK, 'F.Fab', 0.1)
    t += rect(-bx - CRT, Y_ENTRY - CRT, bx + CRT, Y_BACK + CRT, 'F.CrtYd', 0.05)
    for i, x in enumerate(xs, 1):
        t += ('\t(pad "%d" thru_hole circle\n\t\t(at %s 0 90)\n\t\t(size %s %s)\n\t\t(drill %s)\n'
              '\t\t(layers "*.Cu" "*.Mask")\n\t\t(remove_unused_layers no)\n\t\t(thermal_bridge_angle 0)\n'
              '\t\t(uuid "00000000-0000-0000-0000-000000000000")\n\t)\n') % (i, f(x), f(PAD), f(PAD), f(DRILL))
    t += '\t(embedded_fonts no)\n)\n'
    return name, t


if __name__ == '__main__':
    for n in range(2, 11):
        name, t = footprint(n)
        with open(os.path.join(REPO, 'native', name + '.kicad_mod'), 'w') as fh:
            fh.write(t)
        print(name)
