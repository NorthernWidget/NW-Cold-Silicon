"""Lift a footprint out of a KiCad board file, as a library footprint.

    from from_board import embedded, as_library
    fps = embedded('Okapi.kicad_pcb')            # name -> list of instance blocks
    text = as_library(fps['SD_WURTH_WR-CRD'], 'SD_WURTH_WR-CRD')

The pad and text angles of a rotated instance are un-rotated;
positions are local already. An embedded footprint carries its placement, its reference and value, its pad
nets and the board's uuids. as_library() takes an instance that sits on F.Cu
at rotation 0 (so pad and text angles are the footprint's own), drops the
placement, sets the reference to REF** and the value to the name, removes the
nets, gives every object a fresh uuid, and adds the library file header.
sig() reduces a footprint to its pads and graphic counts, for comparison.
"""
import re,uuid,collections,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
def embedded(pcb):
    t=open(pcb).read(); out=collections.defaultdict(list)
    for m in re.finditer(r'^\t\(footprint "([^"]+)"\n.*?^\t\)\n',t,re.S|re.M):
        out[m.group(1)].append(m.group(0))
    return out
def _at(block):
    m=re.search(r'^\t\t\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)\n',block,re.M)
    return float(m.group(3) or 0), m
def as_library(instances,name):
    cands=sorted([b for b in instances if '\t\t(layer "F.Cu")\n' in b],key=lambda b:abs(_at(b)[0]))
    assert cands, ('no instance of %s on F.Cu'%name)
    b=cands[0]; rot=_at(b)[0]
    b=re.sub(r'^\t\(footprint "[^"]+"\n',
             '(footprint "%s"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n'%name,b,count=1)
    b=re.sub(r'^\t\t\(at -?[\d.]+ -?[\d.]+(?: -?[\d.]+)?\)\n','',b,count=1,flags=re.M)
    if rot:  # pad and text positions are local already; only their angles carry the placement
        def unrot(m):
            a=(float(m.group(3) or 0)-rot)%360
            return '(at %s %s%s)'%(m.group(1),m.group(2),'' if a==0 else ' '+('%g'%a))
        b=re.sub(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)',unrot,b)
    b=re.sub(r'^\t\t\((?:path|sheetname|sheetfile) "[^"]*"\)\n','',b,flags=re.M)
    b=re.sub(r'\(property "Reference" "[^"]*"','(property "Reference" "REF**"',b,count=1)
    b=re.sub(r'\(property "Value" "[^"]*"','(property "Value" "%s"'%name,b,count=1)
    b=re.sub(r'^\t+\(net \d+ "[^"]*"\)\n','',b,flags=re.M)
    b=re.sub(r'\(uuid "[^"]+"\)',lambda m:'(uuid "%s")'%uuid.uuid4(),b)
    return '\n'.join(l[1:] if l.startswith('\t') else l for l in b.split('\n'))
def sig(text):
    from sexp import parse,kids,kid
    node=parse(text); pads=[]
    for p in kids(node,'pad'):
        at=kid(p,'at'); sz=kid(p,'size'); ly=kid(p,'layers'); dr=kid(p,'drill')
        pads.append((p[1],p[2],p[3],tuple(round(float(x),3) for x in at[1:3]),(float(at[3]) if len(at)>3 else 0.0)%360,tuple(round(float(x),3) for x in sz[1:3]),tuple(sorted(ly[1:])) if ly else (),tuple(dr[1:]) if dr else ()))
    g=collections.Counter(x[0] for x in node if isinstance(x,list) and x[0] in ('fp_line','fp_poly','fp_circle','fp_arc','fp_rect'))
    return (tuple(sorted(pads)),tuple(sorted(g.items())))
def from_eagle(brd,pairs,workdir):
    """Convert packages straight from an Eagle board's embedded library with KiCad's importer.

    pairs: [(eagle library name, package name)]. A board that places each
    package once, on top, unrotated, is written and imported with
    `kicad-cli pcb import`, and the footprints are lifted from the result. The
    same converter that built the library from the .lbr files, so a package
    that exists only on a board comes in the same way as the rest."""
    import xml.etree.ElementTree as ET,subprocess
    tree=ET.parse(brd); board=tree.getroot().find('drawing/board'); libs=board.find('libraries')
    want=set(pairs); keep={}
    for L in list(libs):
        pk=L.find('packages')
        for p in list(pk):
            if (L.get('name'),p.get('name')) in want: keep[(L.get('name'),p.get('name'))]=True
            else: pk.remove(p)
        if not len(pk): libs.remove(L)
    missing=want-set(keep); assert not missing, ('package not in the Eagle board',missing)
    els=board.find('elements'); els.clear()
    for s in list(board.find('signals')): board.find('signals').remove(s)
    board.find('plain').clear()
    for i,(lib,name) in enumerate(sorted(want)):
        ET.SubElement(els,'element',name='X%d'%i,library=lib,package=name,value='',x='0',y=str(40*i))
    os.makedirs(workdir,exist_ok=True); gen=os.path.join(workdir,'gen.brd'); out=os.path.join(workdir,'gen.kicad_pcb')
    tree.write(gen,encoding='utf-8',xml_declaration=True)
    p=subprocess.run(['kicad-cli','pcb','import','--format','eagle','-o',out,gen],capture_output=True,text=True); assert p.returncode==0,p.stderr
    emb=embedded(out)
    return {name:as_library(emb[name],name) for lib,name in want}
