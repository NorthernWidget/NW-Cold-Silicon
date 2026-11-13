"""Build nw-cold-silicon.pretty and nw-cold-silicon.kicad_sym from the Eagle libraries.

usage: build.py [--upto KEY] [--workspace DIR]

Converts each source library with kicad-cli (fp upgrade -o, sym upgrade -o),
then merges them in the precedence order of SOURCES. A name that appears in two
sources with identical content (uuid lines ignored) is kept once. A name whose
content differs is kept from the earlier source under its own name and from a
later PRIMARY source under NAME_<key>, so nothing is lost; from an EXTRAS source
(an older fork or copy) only names absent so far are added. A name in
PREFER_FIRST is a collision Andy has settled: the first copy stands, the later
one is not kept, and the later source's symbols point at the first. Every symbol's Footprint field is
rewritten from the Eagle library name to nw-cold-silicon and to the merged
footprint name, since the merged library has one nickname. Two symbols that
differ only in BOM properties (BOM_PROPS: description, datasheet, manufacturer
and part numbers) count as identical and the earlier one is kept, so the
dedicated passives library's purchasing data stands. ALIASES collapses a second
copy under another name onto the first; BOARD_PREFERRED takes a package from a
board's Eagle file where that is the newer drawing; SCHEMATIC_LIFT and
POWER_LIFT take symbols from a board's imported project library, the latter
as KiCad power symbols; COLLISIONS.md
says so for each. The script writes PROVENANCE.md and COLLISIONS.md itself, so
every number in them is the build's.
Footprints drawn in KiCad rather than converted (native/*.kicad_mod) are copied in
under their own names; a name a converted footprint already holds stops the build.
--upto stops after the named source, for one commit per source.
"""
import os,re,sys,shutil,subprocess,tempfile,uuid,datetime,collections,glob
import xml.etree.ElementTree as ET
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from from_board import embedded,as_library,sig,from_eagle
HERE=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.dirname(HERE)
args=sys.argv[1:]
ws=os.path.dirname(REPO); upto=None
if '--workspace' in args: ws=args[args.index('--workspace')+1]
if '--upto' in args: upto=args[args.index('--upto')+1]
SOURCES=[  # key, path under the workspace, kind
 ('passives','Cold-Silicon/bschulz_passives.lbr','PRIMARY'),
 ('bschulz','Cold-Silicon/bschulz.lbr','PRIMARY'),
 ('awickert','NorthernWidget-Eagle-Libraries/awickert.lbr','PRIMARY'),
 ('csandell','NorthernWidget-Eagle-Libraries/csandell.lbr','PRIMARY'),
 ('fork','Cold-Silicon-awickert/bschulz.lbr','EXTRAS'),
 ('old','Cold-Silicon/bschulz_Old.lbr','EXTRAS'),
]
if upto: SOURCES=SOURCES[:[s[0] for s in SOURCES].index(upto)+1]
BOARDS=[  # key, KiCad board, Eagle board (for each element's library of origin); only after every source
 ('okapi','Project-Okapi/Hardware/KiCAD-10import/Okapi.kicad_pcb','Project-Okapi/Hardware/Okapi.brd'),
 ('margay','Project-Margay/Hardware/KiCAD/Margay.kicad_pcb','Project-Margay/Hardware/Margay.brd'),
]
NOTES={  # what is known about a package no source library holds; printed under the Boards table
 'SD_WURTH_WR-CRD':"full-size SD holder, Würth Elektronik 693063010911 (the package's own datasheet link), drawn by Bobby Schulz; in no committed Eagle library. Adafruit's SDCARD has the same pitch and pad count with 4.0 by 1.2 mm signal pads against 1.0 by 1.5 here, a relative and not the source (Andy, 2026-11-02: Bobby's is the one).",
 'USB_C_CUSB31-CFM2AX-01-X':"USB-C receptacle; Okapi.brd and Margay.brd name Adafruit's microbuilder library, which does not hold it in the 2015 release that is Adafruit's current master.",
 'SOT23-3@1':"Eagle's name for a second SOT23-3 variant in bschulz; identical on the Okapi and Margay boards.",
 'USB_MICRO_VERT_MOLEX':"from Bobby's working copy of bschulz, never committed to Cold-Silicon.",
 'PARTICLE_M.2EKEY_NOPROG':"from Bobby's working copy of bschulz, never committed to Cold-Silicon.",
}
PREFER_FIRST={  # a same-name collision between PRIMARY sources settled by decision: the later copy is not kept, its symbols point at the first
 'C0402':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'C0603':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'C0805':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'C1206':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'R0402':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'R0603':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'R0805':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'R1206':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'R2010':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'R2512':"Andy, 2026-11-02: bschulz_passives' for every passive. The passives library is Bobby's later revision (2017-11-16) of the pads in bschulz; every passive on Okapi and Margay but R48 was placed from it.",
 'LTC4412S6':"Andy, 2026-11-02, no doubles: bschulz's (reference U, SOT23-6L, pin SENSE; Okapi U7 uses it). awickert's older drawing (reference IC, TSOT23-6, pin SEN) is used by no board.",
 'LINX_BAT-HLD-012-SMT':"Andy, 2026-11-02: bschulz's. Pads identical; bschulz's puts no solder paste on the 10.16 mm center pad and both boards were built with it; awickert's opens the stencil over the whole pad.",
}
ALIASES={  # a second copy under another name, collapsed onto the first; symbols and boards that named it get the target
 'SOT23-3@1':('SOT23-3',"Eagle's second copy of SOT23-3 in bschulz: identical pads, text size and a 0.0635 against 0.1016 mm mask margin the only differences (Andy, 2026-11-02, no doubles)."),
}
BOARD_PREFERRED={  # a package whose newest drawing is the copy in a board's Eagle file, not the committed .lbr: taken from that board
 '4_40_CLOSE':('margay',"Margay.brd (2024-11-01) draws the mounting hole's outer circle on the Reference layer; bschulz.lbr (2022-12-15) draws it on silkscreen, where it is clipped by the board edge on Margay. The board's is the later drawing."),
 'LINX_BAT-HLD-012-SMT':('okapi',"Okapi.brd (2024-11-02) carries Bobby's later drawing with the silkscreen outline; bschulz.lbr (2022-12-15) has the same pads and no outline. Andy, 2026-11-02: bschulz's."),
}
SCHEMATIC_LIFT={  # symbols that exist only in a board's imported project library (Bobby's working copy, or a library not in the workspace)
 # A source is Repo@commit:path, read from that repository's git object, because an import library is retired once nothing names it
 # (Okapi's went with f5ae35d) and the lift must still build. The commit is the last at which the file and the sheets hold every lifted definition.
 'Project-Okapi@11776ab:Hardware/KiCAD-10import/Okapi-eagle-import.kicad_sym':{
   'BAT54C':"dual Schottky, bschulz working copy, not in Cold-Silicon 5823fee",
   'USB_C':"USB-C receptacle symbol, Adafruit's microbuilder library, not in the workspace",
   'B_SERIES_M.2EKEY_NOPROG':"Particle B-series M.2 connector, bschulz working copy",
   'USB_MICROVERT':"vertical micro-USB, bschulz working copy",
   'BMA456':"Bosch accelerometer, bschulz working copy",
   'MLX90393':"Melexis magnetometer, bschulz working copy",
 },
 'Project-Margay@fc9e682:Hardware/KiCAD/Margay-eagle-import.kicad_sym':{
   'SDMMCWR-CRD':"SD/MMC socket, the Wurth WR-CRD device of bschulz's SDMMC deviceset, bschulz working copy (the committed library has SCDA, 18650 and 06132 only); the KiCad 7 import embedded it in Margay_1 and never wrote it to its library file",
 },
}
POWER_LIFT={  # the import's supply symbols become KiCad power symbols: (power), reference #PWR, the rail's name as value and pin name
 'Project-Okapi@11776ab:Hardware/KiCAD-10import/Okapi-eagle-import.kicad_sym':{'GND':'GND','3V3_AUX':'3V3_AUX','3V3_CORE':'3V3_CORE'},
}
def git_show(source):
    """'Repo@commit:path' -> the file at that commit of the workspace repository Repo."""
    repo,rest=source.split('@',1); rev,path=rest.split(':',1)
    return subprocess.run(['git','-C',os.path.join(ws,repo),'show',f'{rev}:{path}'],capture_output=True,text=True,check=True).stdout
def git_sheets(source):
    """The .kicad_sch files beside a 'Repo@commit:path' library at that commit, as (name, text)."""
    repo,rest=source.split('@',1); rev,path=rest.split(':',1); d=os.path.dirname(path)
    names=subprocess.run(['git','-C',os.path.join(ws,repo),'ls-tree','--name-only',rev,d+'/'],capture_output=True,text=True,check=True).stdout.split()
    return [(f,git_show(f'{repo}@{rev}:{f}')) for f in sorted(names) if f.endswith('.kicad_sch')]
def lift_symbol(source,name,new=None,power=False):
    t=git_show(source)
    m=re.search(r'^\t\(symbol "'+re.escape(name)+r'"\n.*?^\t\)\n',t,re.S|re.M)
    if m: b=m.group(0)
    else:   # a definition the importer embedded in a sheet and never wrote to the library file
        nick=os.path.basename(source.split(':',1)[1])[:-len('.kicad_sym')]; b=None
        for f,text in git_sheets(source):
            m=re.search(r'^\t\t\(symbol "'+re.escape(nick+':'+name)+r'"\n.*?^\t\t\)\n',text,re.S|re.M)
            if m: b='\n'.join(l[1:] for l in m.group(0).split('\n')).replace('(symbol "%s:%s"'%(nick,name),'(symbol "%s"'%name,1); break
        assert b,(source,name)
    new=new or name
    b=re.sub(r'^\t\(symbol "'+re.escape(name)+'"','\t(symbol "%s"'%new,b,count=1)
    b=re.sub(r'\(symbol "'+re.escape(name)+r'_(\d+_\d+)"',lambda q:'(symbol "%s_%s"'%(new,q.group(1)),b)
    b=re.sub(r'\(property "Footprint" "[^"]*:([^"]*)"',lambda q:'(property "Footprint" "%s:%s"'%(LIB,q.group(1)),b)
    b=re.sub(r'^(\t+)\(text "\$\{DISP\}"\n(?:.*\n)*?\1\)\n','',b,flags=re.M)   # the GUI import's unresolvable text, at whatever depth it sits
    if power:
        if not re.search(r'^\t\t\(power',b,re.M): b=b.replace('\t(symbol "%s"\n'%new,'\t(symbol "%s"\n\t\t(power)\n'%new,1)
        b=re.sub(r'\(exclude_from_sim \w+\)','(exclude_from_sim yes)',b,count=1); b=re.sub(r'\(in_bom \w+\)','(in_bom no)',b,count=1); b=re.sub(r'\(on_board \w+\)','(on_board no)',b,count=1)
        b=re.sub(r'\(property "Reference" "[^"]*"','(property "Reference" "#PWR"',b,count=1)
        b=re.sub(r'\(property "Value" "[^"]*"','(property "Value" "%s"'%new,b,count=1)
        b=re.sub(r'\(name "[^"]*"',lambda q:'(name "%s"'%new,b)
    return b
EAGLE_KEY={'bschulz_passives':'passives','bschulz':'bschulz','awickert':'awickert','csandell':'csandell'}
LIB='nw-cold-silicon'; PRETTY=os.path.join(REPO,LIB+'.pretty'); SYM=os.path.join(REPO,LIB+'.kicad_sym')
def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True); return p.returncode,(p.stdout+p.stderr).strip()
def git(path,*a):
    return subprocess.run(['git','-C',os.path.dirname(path)]+list(a),capture_output=True,text=True).stdout.strip()
def norm(t): return re.sub(r'\n\s*\(uuid "[^"]+"\)','',t)
BOM_PROPS=('Description','Datasheet','MF','MPN','DIGIKEY','DIGIKEY_PN','MOUSER','PARTNO')
def nodesc(t):
    """The symbol with its BOM-only properties removed and the rest of its properties sorted:
    what is left is the drawing, the pins, the footprint and the other fields, whatever their order
    and wherever a hidden field was stacked."""
    t=re.sub(r'\t\t\(property "(?:%s)" "(?:[^"\\]|\\.)*"\n.*?\n\t\t\)\n'%'|'.join(BOM_PROPS),'',t,flags=re.S)
    props=re.findall(r'\t\t\(property "[^"]*" "(?:[^"\\]|\\.)*"\n.*?\n\t\t\)\n',t,flags=re.S)
    props=[re.sub(r'\(at [^)]*\)','(at)',q) if '(hide yes)' in q else q for q in props]   # a hidden field's position is where the GUI stacked it
    rest=re.sub(r'\t\t\(property "[^"]*" "(?:[^"\\]|\\.)*"\n.*?\n\t\t\)\n','',t,flags=re.S)
    return rest+''.join(sorted(props))
def refoot(block,fpmap):
    def rep(m):
        name=m.group(1).split(':')[-1]; return '(property "Footprint" "%s:%s"'%(LIB,fpmap.get(name,name))
    return re.sub(r'\(property "Footprint" "([^"]*)"',rep,block)
def split_syms(t):
    starts=[m.start() for m in re.finditer(r'^\t\(symbol "',t,re.M)]
    head=t[:starts[0]]; end=t.rfind('\n)'); blocks={}
    for i,s in enumerate(starts):
        e=starts[i+1] if i+1<len(starts) else end+1
        b=t[s:e]; name=re.match(r'\t\(symbol "([^"]+)"',b).group(1); blocks[name]=b
    return head,blocks
def rename_sym(block,old,new):
    return re.sub(r'\(symbol "'+re.escape(old)+r'(?=["_])',lambda m:'(symbol "'+new,block)
tmp=tempfile.mkdtemp(prefix='nwcs-'); kv=run(['kicad-cli','version'])[1]
prov=['# Provenance','',f'Built {datetime.date.today()} by tools/build.py with kicad-cli {kv}. Sources, in precedence order:','',
      '| key | kind | file | repository commit | packages | symbols | converter warnings |','|---|---|---|---|---|---|---|']
coll=['# Collisions','','Names that occur in more than one source. "kept once" means the later copy was identical (uuid lines ignored) and was dropped. "both" means the content differs and the later PRIMARY copy is in the library as NAME_key. "older copy skipped" means an EXTRAS source carried a different version of a name already present. Decide and rename at will; rerun build.py after changing SOURCES or this rule.','',
      '| name | kind | kept from | also in | action |','|---|---|---|---|---|']
fps={}; fpsrc={}; syms={}; symsrc={}; head=None; fpmap={}
for key,rel,kind in SOURCES:
    src=os.path.join(ws,rel); d=os.path.join(tmp,key)
    rc1,o1=run(['kicad-cli','fp','upgrade','-o',d+'.pretty',src]); rc2,o2=run(['kicad-cli','sym','upgrade','-o',d+'.kicad_sym',src])
    assert rc1==0 and rc2==0,(key,o1,o2)
    warn=sorted(set(re.sub(r'^\S+ \S+: ','',l) for l in (o1+'\n'+o2).splitlines() if 'Ignoring' in l))
    npk=0; nsy=0
    for f in sorted(os.listdir(d+'.pretty')):
        if not f.endswith('.kicad_mod'): continue
        name=f[:-10]; t=open(os.path.join(d+'.pretty',f)).read(); npk+=1; fpmap.setdefault(key,{})[name]=name
        if name in ALIASES:
            fpmap[key][name]=ALIASES[name][0]; coll.append(f'| {name} | footprint | – | {key} | collapsed onto `{ALIASES[name][0]}`: {ALIASES[name][1]} |'); continue
        if name not in fps: fps[name]=t; fpsrc[name]=key; continue
        if norm(fps[name])==norm(t): coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | kept once |'); continue
        if kind=='PRIMARY' and name in PREFER_FIRST:
            coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | kept the first by decision: {PREFER_FIRST[name]} |'); continue
        if kind=='PRIMARY':
            new=f'{name}_{key}'; fps[new]=t.replace(f'(footprint "{name}"',f'(footprint "{new}"',1); fpsrc[new]=key; fpmap[key][name]=new
            coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | both: `{new}` |')
        else: coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | older copy skipped |')
    h,blocks=split_syms(open(d+'.kicad_sym').read()); head=head or h
    for name,b in blocks.items():
        nsy+=1; b=refoot(b,fpmap.get(key,{}))
        if name not in syms: syms[name]=b; symsrc[name]=key; continue
        if syms[name]==b: coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | kept once |'); continue
        if nodesc(syms[name])==nodesc(b): coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | kept once, BOM fields differ (the first source\'s stand) |'); continue
        if kind=='PRIMARY' and name in PREFER_FIRST:
            coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | kept the first by decision: {PREFER_FIRST[name]} |'); continue
        if kind=='PRIMARY':
            new=f'{name}_{key}'; syms[new]=rename_sym(b,name,new); symsrc[new]=key
            coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | both: `{new}` |')
        else: coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | older copy skipped |')
    prov.append(f'| {key} | {kind} | `{rel}` | {git(src,"log","-1","--format=%h %cs","--",os.path.basename(src))} | {npk} | {nsy} | {"; ".join(warn) or "–"} |')
if not upto:
    for libfile,names in SCHEMATIC_LIFT.items():
        for name,why in names.items():
            assert name not in syms,(name,'already in the library')
            syms[name]=lift_symbol(libfile,name); symsrc[name]='schematic:'+libfile.split('@')[0]
            coll.append(f'| {name} | symbol | – | {libfile.split("@")[0]} | lifted from the imported project library: {why} |')
    for libfile,names in POWER_LIFT.items():
        for name,new in names.items():
            assert new not in syms,(new,'already in the library')
            syms[new]=lift_symbol(libfile,name,new,power=True); symsrc[new]='power:'+libfile.split('@')[0]
            coll.append(f'| {new} | symbol | – | {libfile.split("@")[0]} | power symbol for the rail, from the import\'s supply symbol |')
    for name,(bkey,why) in BOARD_PREFERRED.items():
        _,pcb,brd=[b for b in BOARDS if b[0]==bkey][0]
        lib=[e.get('library') for e in ET.parse(os.path.join(ws,brd)).getroot().iter('element') if e.get('package')==name][0]
        fps[name]=from_eagle(os.path.join(ws,brd),[(lib,name)],os.path.join(tmp,'brd',bkey))[name]; fpsrc[name]=f'board:{bkey}'
        coll.append(f'| {name} | footprint | board {bkey} | {", ".join(k for k,v in fpmap.items() if name in v)} | taken from the board\'s Eagle file by decision: {why} |')
    prov+=['','## Boards','','Footprints embedded in the KiCad boards, each matched to the library through its element\'s Eagle library of origin. A name no source library holds is added from the Eagle board\'s own package definition through `kicad-cli pcb import`, the converter that built the rest. Columns: identical to the library copy in pads and graphics; same pads but the KiCad board\'s copy (a June 2026 import) draws the graphics or sizes a non-plated hole differently; pads differ (the board copy is NOT taken over; COLLISIONS.md lists it); unchecked means the board has no front-side instance to compare.','',
           '| board | file | embedded names | identical | pads identical | pads differ | added | unchecked |','|---|---|---|---|---|---|---|---|']
    # a native footprint (native/, drawn in KiCad) has no Eagle origin, so the board pass never looks for it in an Eagle
    # board; it is copied in from native/ below (the dual 0402/0603 land on Okapi from 2026-11-08 stopped the build here)
    NATIVE={os.path.basename(f)[:-len('.kicad_mod')] for f in glob.glob(os.path.join(REPO,'native','*.kicad_mod'))}
    for bkey,pcb,brd in BOARDS:
        el={e.get('name'):(e.get('library'),e.get('package')) for e in ET.parse(os.path.join(ws,brd)).getroot().iter('element')}
        up=os.path.join(tmp,'brd',bkey+'.kicad_pcb'); os.makedirs(os.path.dirname(up),exist_ok=True); shutil.copy(os.path.join(ws,pcb),up)
        rc,o=run(['kicad-cli','pcb','upgrade','--force',up]); assert rc==0,o   # older boards use another layout
        emb=embedded(up); n_id=n_pad=n_dif=n_add=n_unc=0
        for full,insts in sorted(emb.items()):
            n=full.split(':')[-1].replace('_528','')
            if n in NATIVE: continue
            groups=collections.defaultdict(list)
            for b in insts:
                ref=re.search(r'\(property "Reference" "([^"]*)"',b).group(1); groups[el.get(ref,(None,None))[0]].append(b)
            for lib,ins in groups.items():
                key=EAGLE_KEY.get(lib); merged=fpmap.get(key,{}).get(n) if key else None
                if merged is None and n in ALIASES: merged=ALIASES[n][0]
                if merged is None and n in fps: merged=n
                if merged is None:
                    fps[n]=from_eagle(os.path.join(ws,brd),[(lib,n)],os.path.join(tmp,'brd',bkey))[n]; fpsrc[n]=f'board:{bkey}'; fpmap.setdefault(bkey,{})[n]=n; merged=n; n_add+=1; added=True
                else: added=False
                try: bs=sig(as_library(ins,n))
                except AssertionError:
                    n_unc+=1; coll.append(f'| {n} | footprint | {fpsrc[merged]} | board {bkey} ({lib}) | {"added from the Eagle board; " if added else ""}unchecked: no front-side instance |'); continue
                ls=sig(fps[merged])
                if ls==bs:
                    n_id+=1
                    if added: coll.append(f'| {n} | footprint | – | board {bkey} ({lib}) | added from the Eagle board; KiCad board copy identical |')
                elif ls[0]==bs[0]:
                    n_pad+=1; coll.append(f'| {n} | footprint | {fpsrc[merged]} as `{merged}` | board {bkey} ({lib}, {len(ins)} placed) | {"added from the Eagle board; " if added else ""}same pads, KiCad board copy draws graphics differently |')
                else:
                    n_dif+=1; coll.append(f'| {n} | footprint | {fpsrc[merged]} as `{merged}` | board {bkey} ({lib}, {len(ins)} placed) | {"added from the Eagle board; " if added else ""}pads differ: KiCad board copy not taken over |')
        prov.append(f'| {bkey} | `{pcb}` | {len(emb)} | {n_id} | {n_pad} | {n_dif} | {n_add} | {n_unc} |')
    prov+=['','Added from the boards (graphics the importer put on the Rescue layer, from Eagle layers it does not map, are dropped: %d items; a non-plated hole\'s pad, which that importer makes 0.254 mm wider than the drill, is set to the drill as the library converter and Eagle have it: %d pads):'%(getattr(as_library,'dropped_rescue',0),getattr(as_library,'npth_resized',0)),'']+[f'- `{n}`: {NOTES.get(n,"no note")}' for n in sorted(k for k,v in fpsrc.items() if v.startswith('board:'))]
# the footprints are written beside the library and swapped in only when the build has passed its checks, so an
# aborted build leaves the committed library in place (a NameError once emptied it)
PRETTY_OUT=PRETTY; PRETTY=os.path.join(REPO,LIB+'.building.pretty')   # kicad-cli reads the library type off the extension
if os.path.isdir(PRETTY): shutil.rmtree(PRETTY)
os.makedirs(PRETTY)
GRAPHIC={  # parts that are artwork, not components: no BOM line, no pick-and-place row, no simulation
 'NWLOGO':'Northern Widget logo, silkscreen','NWLOGO_MED':'Northern Widget logo, medium, silkscreen','NW_LOGO_1IN':'Northern Widget logo, one inch',
 'ALOG_LOGO_V0':'ALog logo, v0','ALOG_LOGO_V0_SMALL':'ALog logo, v0, 5.5 mm','ALOG_LOGO_V0_5.5MM':'ALog logo, v0, 5.5 mm','ALOG_LOGO_V1_SMALL':'ALog logo, v1, 5.5 mm','ALOG_LOGO_V1_5.5MM':'ALog logo, v1, 5.5 mm',
 'OSHW-LOGO-L':'Open Source Hardware logo, large','OSHW-LOGO-M':'Open Source Hardware logo, medium','OSHW-LOGO-S':'Open Source Hardware logo, small','OSHW-LOGO-MINI':'Open Source Hardware logo, mini',
 'OSHW-LOGO-L_COPPER':'Open Source Hardware logo, large, copper','OSHW-LOGO-M_COPPER':'Open Source Hardware logo, medium, copper','OSHW-LOGO-S_COPPER':'Open Source Hardware logo, small, copper',
 'OSHW-LOGOL':'Open Source Hardware logo, large','OSHW-LOGOM':'Open Source Hardware logo, medium','OSHW-LOGOS':'Open Source Hardware logo, small','OSHW-LOGOMINI':'Open Source Hardware logo, mini',
 'OSHW-LOGOL-COPPER':'Open Source Hardware logo, large, copper','OSHW-LOGOM-COPPER':'Open Source Hardware logo, medium, copper','OSHW-LOGOS-COPPER':'Open Source Hardware logo, small, copper',
}
def graphic_fp(t,name):
    t=re.sub(r'^\t\(descr "[^"]*"\)\n','',t,flags=re.M)
    t=re.sub(r'^\t\(property "Description" ""','\t(property "Description" "%s"'%GRAPHIC[name],t,count=1,flags=re.M)
    t=re.sub(r'^\t\(property "Reference" "[^"]*"','\t(property "Reference" "LOGO"',t,count=1,flags=re.M)
    t=re.sub(r'^\t\(property "Value" "[^"]*"','\t(property "Value" "%s"'%name,t,count=1,flags=re.M)
    if '(attr ' not in t: t=re.sub(r'^(\t\(duplicate_pad_numbers_are_jumpers [^)]*\)\n)',r'\1\t(attr exclude_from_pos_files exclude_from_bom)\n',t,count=1,flags=re.M)
    return t.replace('(layer "F.Cu")\n\t(descr','(layer "F.Cu")\n\t(descr "%s")\n\t(descr'%GRAPHIC[name],1) if False else re.sub(r'^\t\(layer "F\.Cu"\)\n',lambda m:m.group(0)+'\t(descr "%s")\n'%GRAPHIC[name],t,count=1,flags=re.M)
def fmt6(v):
    s=('%.6f'%v).rstrip('0').rstrip('.'); return '0' if s in ('-0','') else s
def artwork_from_fp(fp,scale=2.0):
    """The footprint's front-silkscreen drawing as symbol graphics, scaled and with y up (a symbol's y axis
    points up, a footprint's down). Lines become polylines, filled polygons filled polylines."""
    out=[]
    for m in re.finditer(r'^\t\((fp_line|fp_poly|fp_circle|fp_arc)\n((?:\t\t.*\n)+?)\t\)\n',fp,re.M):
        kind,body=m.group(1),m.group(2)
        if '(layer "F.SilkS")' not in body: continue
        pts=[(float(a)*scale,-float(b)*scale) for a,b in re.findall(r'\((?:start|mid|end|xy|center) (-?[\d.]+) (-?[\d.]+)\)',body)]
        w=re.search(r'\(width ([\d.]+)\)',body); w=float(w.group(1))*scale if w else 0
        if kind=='fp_line':
            out.append('\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy %s %s) (xy %s %s)\n\t\t\t\t)\n\t\t\t\t(stroke\n\t\t\t\t\t(width %s)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n'%(fmt6(pts[0][0]),fmt6(pts[0][1]),fmt6(pts[1][0]),fmt6(pts[1][1]),fmt6(w)))
        elif kind=='fp_poly':
            out.append('\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t%s\n\t\t\t\t)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type outline)\n\t\t\t\t)\n\t\t\t)\n'%' '.join('(xy %s %s)'%(fmt6(x),fmt6(y)) for x,y in pts+pts[:1]))
        elif kind=='fp_circle':
            r=((pts[1][0]-pts[0][0])**2+(pts[1][1]-pts[0][1])**2)**0.5
            out.append('\t\t\t(circle\n\t\t\t\t(center %s %s)\n\t\t\t\t(radius %s)\n\t\t\t\t(stroke\n\t\t\t\t\t(width %s)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n'%(fmt6(pts[0][0]),fmt6(pts[0][1]),fmt6(r),fmt6(w)))
        elif kind=='fp_arc':
            out.append('\t\t\t(arc\n\t\t\t\t(start %s %s)\n\t\t\t\t(mid %s %s)\n\t\t\t\t(end %s %s)\n\t\t\t\t(stroke\n\t\t\t\t\t(width %s)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n'%(fmt6(pts[0][0]),fmt6(pts[0][1]),fmt6(pts[1][0]),fmt6(pts[1][1]),fmt6(pts[2][0]),fmt6(pts[2][1]),fmt6(w)))
    return ''.join(out)
def graphic_sym(b,name):
    b=re.sub(r'\(exclude_from_sim \w+\)','(exclude_from_sim yes)',b,count=1); b=re.sub(r'\(in_bom \w+\)','(in_bom no)',b,count=1); b=re.sub(r'\(in_pos_files \w+\)','(in_pos_files no)',b,count=1)
    # the symbol draws the logo itself (the footprint's silkscreen at twice its size) in place of a stand-in text
    art=artwork_from_fp(fps[name]) if name in fps else ''
    if art:
        b=re.sub(r'^\t\t\(symbol "%s_\d+_\d+"\n(?:.*\n)*?\t\t\)\n'%re.escape(name),'',b,flags=re.M)   # every unit body goes
        b=re.sub(r'^\t\t\(embedded_fonts',lambda m:'\t\t(symbol "%s_0_1"\n%s\t\t)\n'%(name,art)+m.group(0),b,count=1,flags=re.M)
    b=re.sub(r'\(property "Reference" "[^"]*"','(property "Reference" "LOGO"',b,count=1)
    b=re.sub(r'\(property "Value" "[^"]*"','(property "Value" "%s"'%name,b,count=1)
    b=re.sub(r'\(property "Description" "[^"]*"','(property "Description" "%s"'%GRAPHIC[name],b,count=1)
    return b
ngr=0
for name in list(fps):
    if name in GRAPHIC: fps[name]=graphic_fp(fps[name],name); ngr+=1
for name in list(syms):
    if name in GRAPHIC: syms[name]=graphic_sym(syms[name],name); ngr+=1
PIN_TYPES={  # a pin whose electrical type the Eagle import got wrong, with the datasheet that says so (the import types every non-power pin input)
 ('TPL5111DDC','DRVN'):('output',"TI SNAS659B: DRVn is the timer's output, asserted every interval to drive a load switch's enable (Okapi U10 ON)"),
 # the regulators' and switches' outputs, typed power input by the import (Okapi CHECKS-TODO ERC item 6): each is the part's output pin by its datasheet
 ('TLV61220DBV','VOUT'):('power_out',"TI SLVSBD8: boost converter output (Okapi 5V_LP)"),
 ('TPS6103RSA','VOUT'):('power_out',"TI SLUS534: boost converter output, three pins (Okapi 5V_AUX)"),
 ('TPS210','OUT'):('power_out',"TI SLVS388 (TPS2105): power multiplexer output (Okapi V_CORE)"),
 ('MIC2544MSOP','OUT'):('power_out',"Microchip MIC2544/2545: current-limited switch output, two pins (Okapi VBUS_PRIME, VBUS_SEC)"),
 ('TPS22917DBV','VOUT'):('power_out',"TI SLVSCX1: load switch output (Okapi V_HP, FEATHER_BAT)"),
 ('TPS797','VOUT'):('power_out',"TI SLVS350 (TPS797xx): LDO output (Okapi 3V3_CORE); the import typed every pin of this symbol bidirectional"),
 # the switch nodes, typed power input by the import, which left them undriven in ERC (Okapi DECISIONS item 5a, 2026-11-10)
 ('TLV61220DBV','SW'):('input',"TI SLVSB53A pin table: SW is I, 'Boost and rectifying switch input' (Okapi U1)"),
 ('TPS6103RSA','SW'):('input',"TI SLUS534G pin table: SW is I, 'Boost and rectifying switch input', two pins (Okapi U3)"),
 ('TPS6282DLC','SW'):('power_out',"TI SLVSDV6C pin table: SW is Power, 'Switch node, connected to the internal MOSFET switches'; power output as KiCad's own TPS62822 symbol (Okapi U2)"),
 ('TPS797','VIN'):('power_in',"TI SLVS350: LDO input"),
 ('TPS797','GND'):('power_in',"TI SLVS350: ground"),
 ('MIC9409C6','VOUT'):('power_out',"Microchip MIC94090/1/2/3: load switch output (Okapi 3V3_CORE_ISO)"),
 ('ADS111','ADDR'):('input',"TI SBAS444 (ADS1115): ADDR is the I2C address select input; the import typed it bidirectional"),
 ('PAC1934QFN','VDD_IO'):('power_in',"Microchip PAC1934 DS20005850: VDD_IO is the I/O supply; the import typed it open collector"),
 # pins the import typed bidirectional, which ERC reports against every PWR_FLAG and power output on their nets
 ('LT3652DD','VIN'):('power_in',"ADI LT3652 datasheet: input supply"),
 ('LT3652DD','VIN_REG'):('input',"ADI LT3652: input voltage regulation reference"),
 ('LT3652DD','~{SHDN}'):('input',"ADI LT3652: shutdown input"),
 ('LT3652DD','~{CHRG}'):('open_collector',"ADI LT3652: open-collector status output"),
 ('LT3652DD','~{FAULT}'):('open_collector',"ADI LT3652: open-collector status output"),
 ('LT3652DD','TIMER'):('passive',"ADI LT3652: timer capacitor pin"),
 ('LT3652DD','VFB'):('input',"ADI LT3652: feedback input"),
 ('LT3652DD','NTC'):('input',"ADI LT3652: thermistor input"),
 ('LT3652DD','BAT'):('power_out',"ADI LT3652: charger output to the battery (Okapi V_LI)"),
 ('LT3652DD','SENSE'):('input',"ADI LT3652: current sense input"),
 ('LT3652DD','BOOST'):('passive',"ADI LT3652: bootstrap capacitor pin"),
 ('LT3652DD','GND_PAD'):('power_in',"ADI LT3652: ground"),
 ('FT231X-Q','VCC'):('power_in',"FTDI DS_FT231X: supply"),
 ('FT231X-Q','VCCIO'):('power_in',"FTDI DS_FT231X: I/O supply"),
 ('FT231X-Q','GND'):('power_in',"FTDI DS_FT231X: ground, three pins"),
 ('FT231X-Q','3V3OUT'):('power_out',"FTDI DS_FT231X: regulator output"),
 ('FT231X-Q','RXD'):('input',"FTDI DS_FT231X: UART receive"),
 ('FT231X-Q','TXD'):('output',"FTDI DS_FT231X: UART transmit"),
 ('FT231X-Q','RTS#'):('output',"FTDI DS_FT231X: handshake output"),
 ('FT231X-Q','DTR#'):('output',"FTDI DS_FT231X: handshake output"),
 ('FT231X-Q','CTS#'):('input',"FTDI DS_FT231X: handshake input"),
 ('FT231X-Q','DSR#'):('input',"FTDI DS_FT231X: handshake input"),
 ('FT231X-Q','DCD#'):('input',"FTDI DS_FT231X: handshake input"),
 ('FT231X-Q','RI#'):('input',"FTDI DS_FT231X: handshake input"),
 ('FT231X-Q','RESET#'):('input',"FTDI DS_FT231X: reset input"),
 ('BME280','VDDIO'):('power_in',"Bosch BST-BME280-DS002: interface supply"),
 ('BME280','CSB'):('input',"Bosch BST-BME280-DS002: chip select / interface select input"),
 ('BME280','SCK'):('input',"Bosch BST-BME280-DS002: serial clock input"),
 ('BME280','SDO'):('input',"Bosch BST-BME280-DS002: I2C address select input in I2C mode (SPI data out otherwise; Okapi uses I2C)"),
 ('MLX90393','MS/CS'):('input',"Melexis MLX90393 datasheet: mode select / chip select input"),
 ('LTC4412S6','CTL'):('input',"ADI LTC4412 datasheet: control input"),
 # open-drain outputs the import typed input, output or bidirectional, and the TWI pins it typed one way (Okapi re-audit 2026-11-13, SYMBOLS.md)
 ('TPS6282DLC','PG'):('open_collector',"TI SLVSDV6C pin table: PG is O, an open-drain power-good output (Okapi U2)"),
 ('TPS797','PG'):('open_collector',"TI SLVS350 pin table: PG is O, open drain (Okapi U9)"),
 ('TPS6103RSA','LBO'):('open_collector',"TI SLUS534 pin table: LBO, low-battery output, open drain (Okapi U3)"),
 ('LTC4412S6','STAT'):('open_collector',"ADI LTC4412 Pin Functions: STAT (Pin 4) is an open-drain output (Okapi U7)"),
 ('ADS111','ALERT'):('open_collector',"TI SBAS444 Table 4-1: ALERT/RDY, open-drain output (Okapi U33)"),
 ('DS3231M','SQW'):('open_collector',"Maxim DS3231M pin description: INT/SQW, an open-drain pin that requires an external pullup (Okapi and Margay RTC1)"),
 ('ATMEGA1284M','(PCINT16/SCL)PC0'):('bidirectional',"Microchip ATmega1284P: PC0 is the TWI clock, driven and read (Okapi and Margay IC1)"),
 ('ATMEGA1284M','(PCINT17/SDA)PC1'):('bidirectional',"Microchip ATmega1284P: PC1 is the TWI data line, driven and read (Okapi and Margay IC1)"),
 ('PCA9634QFN','SCL'):('input',"NXP PCA9634 Table 3: SCL is I (Okapi U45; the import had SCL and SDA's types the other way round)"),
 ('PCA9634QFN','SDA'):('bidirectional',"NXP PCA9634 Table 3: SDA is I/O (Okapi U45)"),
 ('TPS22916YFP','VOUT'):('power_out',"TI SLVSCT1 (TPS22916): load switch output (Margay U8)"),
 ('MAX6070AAUT','VIN'):('power_in',"Maxim MAX6070 datasheet: supply input (Margay U13); the import typed every pin bidirectional"),
 ('MAX6070AAUT','GND'):('power_in',"Maxim MAX6070: ground"),
 ('MAX6070AAUT','EN'):('input',"Maxim MAX6070: enable input"),
 ('MAX6070AAUT','FILT'):('passive',"Maxim MAX6070: noise-reduction capacitor pin"),
 ('MAX6070AAUT','OUTF'):('output',"Maxim MAX6070: reference output, force (an output, not a supply: it feeds an ADC input on Margay)"),
 ('MAX6070AAUT','OUTS'):('passive',"Maxim MAX6070: reference output, sense"),
}
# a discrete part's pins are passive, KiCad's own typing for every diode, LED, transistor and fuse in its library; the
# import typed them bidirectional or power input, which made every LED a power sink and every MOSFET a driver
PASSIVE={
 'LED0603':"an LED (Okapi D10 to D18)",
 'CLVBA-FKA':"the RGB LED (Okapi D4, D5)",
 'LM4040':"a shunt voltage reference, two terminals (Okapi D6)",
 'MOSFET-NCH-2N7002PW':"an N-channel MOSFET (Okapi Q4, Q7, Q8)",
 'MOSFET-NCH-DMG3404L':"an N-channel MOSFET (Okapi Q1, Q2, Q6)",
 'MOSFET_PCH-FDN360P':"a P-channel MOSFET (Okapi Q3, Q5)",
 'PPTC1.5A':"a resettable fuse (Okapi F1, F2)",
 'BUTTON2.6X1.6':"a tactile switch (Okapi S5)",
 'BUTTON4.2X3.2':"a tactile switch (Okapi S3, S4, S6, S7)",
 'JST_2MM_MALE':"a connector (Okapi J8)",
 'AVRISP-6':"a programming header, a connector (Okapi and Margay ISP1): its RST pin had been typed output and met the MCU's reset output",
}
# PWR_FLAG, KiCad's own symbol for telling ERC where a rail enters the schematic (a connector, a battery, a passive part),
# lifted verbatim from the KiCad symbol library (power.kicad_sym, CC-BY-SA 4.0 with the KiCad libraries' exception),
# so the boards need no second symbol library
KICAD_POWER='/usr/share/kicad/symbols/power.kicad_sym'
if os.path.exists(KICAD_POWER):
    kp=open(KICAD_POWER).read(); i=kp.index('\n\t(symbol "PWR_FLAG"'); j=kp.index('\n\t(symbol "',i+10)
    syms['PWR_FLAG']=kp[i+1:j+1]; symsrc['PWR_FLAG']='kicad power.kicad_sym'
    coll.append('| PWR_FLAG | symbol | – | kicad | lifted verbatim from the KiCad symbol library (power.kicad_sym) |')
else:
    raise SystemExit('KiCad symbol library not found at %s: PWR_FLAG cannot be lifted'%KICAD_POWER)
# pins a symbol stacks on one point: KiCad joins them by geometry, where Eagle kept each pad its own. The k-th pin
# of the name is moved k steps along the direction given (symbol coordinates, 2.54 mm a step), so each can carry
# its own flag and its own net; the Okapi micro-USB's six shell slots were one joined net in KiCad and six
# unconnected pads in Eagle (Andy, 2026-11-04: match the way the Eagle boards printed).
# pins to drop before the spread: a pad that shares its number with another (PAD_RENUMBER below) has no pin of its own
PIN_DROP={'USB_MICROVERT':(('P$2','P$4','P$6'),"the shell's second hole of each pair shares its pad number with the first"),
          'BATTERY_COIN12MM':(('POWER1',),"the coin holder's second + spring shares its pad number with the first (PAD_SAME_NUMBER)"),
          'BATTERY_COIN10MM':(('BATT+2',),"the same, for the 10 mm clip")}
for name,(numbers,why) in PIN_DROP.items():
    b=syms[name]; k=0
    for num in numbers:
        b,n=re.subn(r'\t\t\t\(pin \w+ \w+\n(?:(?!\t\t\t\(pin ).*\n)*?\t\t\t\t\(number "%s"\n(?:.*\n)*?\t\t\t\)\n'%re.escape(num),'',b,count=1); assert n==1,(name,num); k+=n
    syms[name]=b; coll.append(f'| {name} | symbol | pins {", ".join(numbers)} | – | dropped: {why} |')
PIN_SPREAD={('USB_MICROVERT','BODY'):((0,-1),"the micro-USB's three shell slots, separate and unconnected as Eagle had them")}
nspread=0
for (name,pin),((dx,dy),why) in PIN_SPREAD.items():
    b=syms[name]; hits=[m.start() for m in re.finditer(re.escape('(name "%s"'%pin),b)]
    for k,i in reversed(list(enumerate(hits))):   # last pin first, so an edit never shifts the text of a pin still to be done
        j=b.rfind('(pin ',0,i); m=re.search(r'\(at (-?[\d.]+) (-?[\d.]+) (\d+)\)',b[j:i])
        x,y=float(m.group(1))+dx*2.54*k,float(m.group(2))+dy*2.54*k
        b=b[:j]+b[j:i].replace(m.group(0),'(at %s %s %s)'%(fmt6(x),fmt6(y),m.group(3)),1)+b[i:]
    assert len(hits)>1,(name,pin); syms[name]=b; nspread+=len(hits); coll.append(f'| {name} | symbol | pins {pin} | – | {len(hits)} stacked pins spread 2.54 mm apart: {why} |')
# a pin the Eagle symbol never had: (name, number, electrical type, x, y, angle in symbol coordinates, why). The
# footprint's pads for it take that number (PAD_SAME_NUMBER), so the pin reaches the pads on the board
PIN_ADD={'USB_C':(('SHIELD','S1','passive',0,-15.24,90),"the receptacle's metal shell (stakes M1-M4), so it can be tied to GND; Eagle left the shell on no net (Andy, 2026-11-11: ground the USB-C shell; Project-Margay #81)")}
for name,((pname,pnum,ptype,x,y,a),why) in PIN_ADD.items():
    b=syms[name]; assert '(number "%s"'%pnum not in b,(name,pnum)
    pin=('\t\t\t(pin %s line\n\t\t\t\t(at %s %s %s)\n\t\t\t\t(length 2.54)\n\t\t\t\t(name "%s"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.524 1.524)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n'
         '\t\t\t\t(number "%s"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 0 0)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n')%(ptype,fmt6(x),fmt6(y),a,pname,pnum)
    i=b.find('\t\t\t(pin '); assert i>0,(name,'no pin to insert before')
    syms[name]=b[:i]+pin+b[i:]; coll.append(f'| {name} | symbol | pin {pname} ({pnum}) | – | added: {why} |')
# a shell drawn as pairs of plated holes joined by a copper bar (Eagle's one shape): the second hole of a pair takes the
# first's pad number, which KiCad treats as one pad, and the bar becomes a primitive of the first pad (a custom-shaped
# pad on an anchor circle), so no loose copper is left for DRC to read as a short or a mask bridge
PAD_RENUMBER={'USB_MICRO_VERT_MOLEX':({'P$2':'P$1','P$4':'P$3','P$6':'P$5'},"the micro-USB shell: three slots of two holes each (Okapi USB2)")}
npadjoin=0
for name,(renum,why) in PAD_RENUMBER.items():
    b=fps[name]
    pads={m.group(1):(float(m.group(2)),float(m.group(3))) for m in re.finditer(r'\(pad "([^"]*)" thru_hole \w+\n\t\t\(at (-?[\d.]+) (-?[\d.]+)',b)}
    for old_,new_ in renum.items():
        b,n=re.subn(r'\(pad "%s" thru_hole'%re.escape(old_),'(pad "%s" thru_hole'%new_,b,count=1); assert n==1,(name,old_)
    # every copper bar whose ends are two pad centers of one number becomes that pad's primitive; the lines go
    bars={}
    def take(m):
        (x1,y1),(x2,y2),w=(float(m.group(1)),float(m.group(2))),(float(m.group(3)),float(m.group(4))),m.group(5)
        ends=[k for k,(px,py) in pads.items() if (abs(px-x1)<1e-6 and abs(py-y1)<1e-6) or (abs(px-x2)<1e-6 and abs(py-y2)<1e-6)]
        if len(ends)!=2: return m.group(0)
        a,c=sorted(ends,key=lambda k:renum.get(k,k)); first=renum.get(a,a)
        if renum.get(c,c)!=first: return m.group(0)
        ax,ay=pads[a]; bx,by=pads[c]
        bars[a]=(bx-ax,by-ay,w); return ''
    b=re.sub(r'^\t\(fp_line\n\t\t\(start (-?[\d.]+) (-?[\d.]+)\)\n\t\t\(end (-?[\d.]+) (-?[\d.]+)\)\n\t\t\(stroke\n\t\t\t\(width ([\d.]+)\)\n(?:.*\n)*?\t\t\(layer "[FB]\.Cu"\)\n(?:.*\n)*?\t\)\n',take,b,flags=re.M)
    for a,(dx,dy,w) in bars.items():
        num=renum.get(a,a)
        def custom(m):
            return m.group(1)+'custom'+m.group(2)+'\t\t(options\n\t\t\t(clearance outline)\n\t\t\t(anchor circle)\n\t\t)\n\t\t(primitives\n\t\t\t(gr_line\n\t\t\t\t(start 0 0)\n\t\t\t\t(end %s %s)\n\t\t\t\t(width %s)\n\t\t\t)\n\t\t)\n'%(fmt6(dx),fmt6(dy),w)
        b,n=re.subn(r'(\(pad "%s" thru_hole )circle(\n\t\t\(at %s %s\)\n(?:.*\n)*?\t\t\(layers [^\n]*\n)'%(re.escape(num),re.escape(fmt6(pads[a][0])),re.escape(fmt6(pads[a][1]))),custom,b,count=1); assert n==1,(name,a)
        npadjoin+=1
    fps[name]=b; coll.append(f'| {name} | footprint | pads {", ".join(f"{o} as {n}" for o,n in renum.items())} | – | {len(bars)} copper bars folded into their pads: {why} |')
# pads that are one terminal of the part: Eagle's device maps one pin to both and routes to either (route="any"),
# so no copper joins them on the board; KiCad joins pads only by number, so the second takes the first's
PAD_SAME_NUMBER={'LINX_BAT-HLD-012-SMT':({'POWER1':'POWER0'},"the coin holder's two + springs are one piece of metal (Margay and Okapi BT1; Eagle contactref route=\"any\")"),
                 'BATT_10MM_CLIP':({'BATT+2':'BATT+1'},"the same, for the 10 mm clip (Eagle route=\"any\")"),
                 'AWICKERT_LINX_BAT-HLD-012-SMT':({'POWER1':'POWER0'},"Andy's copy of the 12 mm holder, the same two springs"),
                 'USB_C_CUSB31-CFM2AX-01-X':({'M1':'S1','M2':'S1','M3':'S1','M4':'S1'},"the four shell stakes are one metal shell, the symbol's SHIELD pin (PIN_ADD; Andy, 2026-11-11: ground the USB-C shell)")}
for name,(renum,why) in PAD_SAME_NUMBER.items():
    b=fps[name]
    for old_,new_ in renum.items():
        b,n=re.subn(r'\(pad "%s" (smd|thru_hole)'%re.escape(old_),lambda m:'(pad "%s" %s'%(new_,m.group(1)),b,count=1); assert n==1,(name,old_)
    # KiCad joins same-numbered pads for the ratsnest only when the footprint says they are jumpers (KiCad 9+)
    b,n=re.subn(r'^\t\(duplicate_pad_numbers_are_jumpers no\)$','\t(duplicate_pad_numbers_are_jumpers yes)',b,count=1,flags=re.M); assert n==1,(name,'jumper flag')
    fps[name]=b; coll.append(f'| {name} | footprint | pads {", ".join(f"{o} as {n}" for o,n in renum.items())}; duplicate_pad_numbers_are_jumpers yes | – | one terminal, two pads: {why} |')
# a footprint whose pads share one solder-mask opening as fabricated: KiCad's allow_soldermask_bridges attribute
FP_ATTRS={'USB_MICRO_VERT_MOLEX':('allow_soldermask_bridges',"the micro-USB's six shell slots share one mask opening on the fabricated board")}
for name,(attr,why) in FP_ATTRS.items():
    b,n=re.subn(r'^\t\(attr ([^)]*)\)',lambda m:'\t(attr %s %s)'%(m.group(1),attr) if attr not in m.group(1) else m.group(0),fps[name],count=1,flags=re.M)
    if n==0: b,n=re.subn(r'^\t\(layer "F\.Cu"\)\n',lambda m:m.group(0)+'\t(attr %s)\n'%attr,fps[name],count=1,flags=re.M)   # a through-hole footprint carries no attr line
    assert n==1,name; fps[name]=b; coll.append(f'| {name} | footprint | attr | – | {attr}: {why} |')
npassive=0
for name,why in PASSIVE.items():
    b,n=re.subn(r'\(pin (?!passive)\w+ (\w+)\n',r'(pin passive \1\n',syms[name]); assert n,(name)
    syms[name]=b; npassive+=n; coll.append(f'| {name} | symbol | every pin | – | electrical type passive: {why} |')
npin=0
for (name,pin),(etype,why) in PIN_TYPES.items():
    b=syms[name]; k=0; pos=0
    while True:
        i=b.find('(name "%s"'%pin,pos)
        if i<0: break
        j=b.rfind('(pin ',0,i)   # the pin block that holds this name: the last "(pin " before it
        m=re.match(r'\(pin (\w+) (\w+)',b[j:]); assert m,(name,pin)
        b=b[:j]+'(pin %s %s'%(etype,m.group(2))+b[j+m.end():]; k+=1; pos=i+1
    assert k,(name,pin); syms[name]=b; npin+=k
    coll.append(f'| {name} | symbol | pin {pin} | – | electrical type {etype}: {why} |')
# a pin the Eagle symbol misnamed, keyed by pad number since the wrong name is shared: (new name, type, datasheet)
PIN_RENAME={
 ('BMA456','1'):('SDO','bidirectional',"Bosch BMA456 pin table: pin 1 is SDO, the I2C address select (GND gives 0x18); the symbol called it GND"),
 ('BMA456','10'):('CSB','input',"Bosch BMA456 pin table: pin 10 is CSB, at VDDIO for I2C mode; the symbol called it VCC"),
 ('MLX90393','4'):('NC','passive',"Melexis MLX90393 Table 3: N/C, 'recommended to connect the N/C pins to Ground'; the symbol called it VSS"),
 ('MLX90393','9'):('NC','passive',"Melexis MLX90393 Table 3: N/C"),
 ('MLX90393','10'):('NC','passive',"Melexis MLX90393 Table 3: N/C"),
 ('MLX90393','14'):('NC','passive',"Melexis MLX90393 Table 3: N/C"),
 ('MLX90393','16'):('NC','passive',"Melexis MLX90393 Table 3: N/C"),
}
for (name,num),(new,etype,why) in PIN_RENAME.items():
    b=syms[name]
    pat=re.compile(r'\(pin \w+ (\w+)\n((?:(?!\t\t\t\(pin ).*\n)*?)(\t+\(name )"[^"]*"((?:(?!\t\t\t\(pin ).*\n)*?\t+\(number "%s"\n)'%re.escape(num))
    b,n=pat.subn(lambda m:'(pin %s %s\n%s%s"%s"%s'%(etype,m.group(1),m.group(2),m.group(3),new,m.group(4)),b); assert n==1,(name,num,n)
    syms[name]=b; coll.append(f'| {name} | symbol | pin {num} | – | named {new}, type {etype}: {why} |')
# a BOM field the Eagle device carried wrong or out of date: (value, why)
SYM_PROPS={
 ('MOSFET_PCH-FDN360P','MF'):('onsemi',"Fairchild has been part of onsemi since 2016; onsemi lists the FDN360P as active (Okapi Q3, Q5; Margay)"),
 ('MOSFET-PCH-FDN360P','MF'):('onsemi',"the same part under its other Eagle name"),
 ('MOSFET_PCH-IRLML2244','MF'):('Infineon',"the IRLML2244 is an International Rectifier part, now Infineon; the Eagle device said Fairchild"),
}
for (name,prop),(val,why) in SYM_PROPS.items():
    b,n=re.subn(r'\(property "%s" "[^"]*"'%re.escape(prop),'(property "%s" "%s"'%(prop,val),syms[name],count=1); assert n==1,(name,prop)
    syms[name]=b; coll.append(f'| {name} | symbol | {prop} | – | {val}: {why} |')
# Eagle's vRestrict (layer 43) in a package means no vias, and the converter writes exactly that: a keepout on every
# copper layer with only vias not allowed. Its bRestrict (layer 42) comes through as a no-copper keepout on B.Cu and its
# tRestrict (41) on F.Cu. All three are kept as converted. (Until 2026-11-11 this build read layer 43 as bRestrict and
# rewrote its six zones, in HL, HC49UP, MICROSD_HIROSE_HINDGED and SWITCH_2.6X1.6, as no-copper keepouts on B.Cu;
# the Eagle conversion audit in NW-Status found it, from both boards' own layer tables.)
# a package whose Eagle restrict sat on the wrong side for the part's datasheet: the zone is moved to the layer and the
# keepout the datasheet asks for (Okapi DECISIONS item 6, 2026-11-10)
KEEPOUT_FIX={'SWITCH_2.6X1.6':('F.Cu',{'tracks':'allowed','vias':'not_allowed','pads':'not_allowed','copperpour':'not_allowed','footprints':'allowed'},
   "Panasonic EVP-BB datasheet, 'Land pattern plan': no land pattern or via holes in the No soldering area under the switch, "
   "or resist over them (solder balls short; extra pattern tilts the switch); a top-side rule, so Bobby's via restrict becomes a F.Cu keepout of pads and vias "
   "and masked tracks stay allowed (Okapi S5)")}
for name,(layer,ko,why) in KEEPOUT_FIX.items():
    t=fps[name]; assert t.count('\t(zone\n')==1,(name,'one keepout zone expected')
    t,n=re.subn(r'(\t\(zone\n\t\t\(layers? )"[^)]*"\s*\)',lambda m:m.group(1)+'"'+layer+'")',t,count=1); assert n==1,name
    t,n=re.subn(r'\(keepout\n(?:.*\n)*?\t\t\)','(keepout\n'+''.join(f'\t\t\t({k} {v})\n' for k,v in ko.items())+'\t\t)',t,count=1); assert n==1,name
    fps[name]=t; coll.append(f'| {name} | footprint | keepout | – | {layer}, '+', '.join(f'{k} {v}' for k,v in ko.items())+f': {why} |')
# A restrict drawn as a closed chain of wires, not a polygon: the converter drops it. Eagle enforced only the wires
# themselves; the area they enclose is the evident intent and is what this writes, as the converter writes a polygon
# on the same layer (layer 43, vRestrict: no vias on any copper layer).
WIRE_RESTRICTS={'SIM_SF72':('Cold-Silicon/bschulz.lbr','43',
   "Bobby's vRestrict over the SIM card, six 0.127 mm wires on layer 43 enclosing 10.39 x 14.35 mm (library only, on no board)")}
import uuid as _uuid
for name,(lbr,layer,why) in WIRE_RESTRICTS.items():
    p=[q for q in ET.parse(os.path.join(ws,lbr)).getroot().iter('package') if q.get('name')==name]; assert len(p)==1,(lbr,name)
    ws_=[(float(w.get('x1')),float(w.get('y1')),float(w.get('x2')),float(w.get('y2'))) for w in p[0] if w.tag=='wire' and w.get('layer')==layer]
    assert ws_ and not any(w.get('curve') for w in p[0] if w.tag=='wire' and w.get('layer')==layer),(name,'straight wires expected')
    pts=[ws_[0][:2],ws_[0][2:]]; left=ws_[1:]
    while left:   # chain the wires end to end
        nxt=[w for w in left if w[:2]==pts[-1] or w[2:]==pts[-1]]; assert len(nxt)==1,(name,'open or branched outline at',pts[-1])
        w=nxt[0]; left.remove(w); pts.append(w[2:] if w[:2]==pts[-1] else w[:2])
    assert pts[0]==pts[-1],(name,'outline not closed'); pts=pts[:-1]
    t=fps[name]; assert '\t(zone\n' not in t,(name,'already has a zone')
    zone=('\t(zone\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(uuid "%s")\n\t\t(hatch edge 0.5)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n'
          '\t\t(min_thickness 0.25)\n\t\t(keepout\n\t\t\t(tracks allowed)\n\t\t\t(vias not_allowed)\n\t\t\t(pads allowed)\n\t\t\t(copperpour allowed)\n'
          '\t\t\t(footprints allowed)\n\t\t)\n\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)\n\t\t(fill\n\t\t\t(thermal_gap 0.5)\n'
          '\t\t\t(thermal_bridge_width 0.5)\n\t\t\t(island_removal_mode 0)\n\t\t)\n\t\t(polygon\n\t\t\t(pts\n\t\t\t\t%s\n\t\t\t)\n\t\t)\n\t)\n')%(
          _uuid.uuid5(_uuid.NAMESPACE_URL,'nw-cold-silicon:%s:%s'%(name,layer)),' '.join('(xy %s %s)'%(fmt6(x),fmt6(-y)) for x,y in pts))
    i=t.rindex('\t(embedded_fonts'); fps[name]=t[:i]+zone+t[i:]
    coll.append(f'| {name} | footprint | keepout | – | F.Cu and B.Cu, vias not allowed: {why} |')
# Eagle's restring: every through-hole pad is fabricated at least drill + 2 x max(25 % of the drill, 5 mil), capped at
# 20 mil of ring (the DRU of every Northern Widget board: rvPadTop 0.25, rlMinPadTop 5mil, rlMaxPadTop 20mil), whatever
# the package drew; KiCad fabricates the drawn pad. A pad drawn under that size is grown to it (Andy, 2026-11-04:
# match the way the Eagle boards printed), both axes by the same amount so an oval stays an oval.
PADRE=re.compile(r'(\(pad "[^"]*" thru_hole \w+\n(?:.*\n)*?\t\t\(size )([\d.]+) ([\d.]+)(\)\n\t\t\(drill )([\d.]+)')
nrestring=0
def restring(m):
    global nrestring
    sx,sy,dr=float(m.group(2)),float(m.group(3)),float(m.group(5))
    want=dr+2*min(max(0.25*dr,0.127),0.508)
    if min(sx,sy)+1e-6>=want: return m.group(0)
    g=want-min(sx,sy); nrestring+=1
    return '%s%s %s%s%s'%(m.group(1),fmt6(sx+g),fmt6(sy+g),m.group(4),m.group(5))
for name in list(fps): fps[name]=PADRE.sub(restring,fps[name])
# Eagle's milled slots: a closed outline on layer 46 (Milling) around a pad's drill is the slot the fabricator routed,
# and KiCad's Eagle reader ignores layer 46, so the converted pad keeps only its round drill and the part's stakes
# would not fit. Each outline is read from the Eagle package (a stadium: two straight sides along its long axis and
# arcs of 360 degrees in all), and the pads whose drill centers lie inside it (one pad number, after PAD_RENUMBER)
# become one oval pad with the slot as its oval drill, at the slot's center and along its axis. A single oval pad keeps
# its copper and rotation; a pair is replaced by the oval its copper already was (two circles and a bar of their width).
# Runs after the restring, which reads round drills only. Andy, 2026-11-11: produce the slots for the USB ports.
MILLED_SLOTS={  # footprint: (Eagle files holding the package, every one checked to agree; why)
 'USB_C_CUSB31-CFM2AX-01-X':(('Project-Okapi/Hardware/Okapi.brd','Project-Margay/Hardware/Margay.brd'),
   "GCT USB4105 shell stakes (Okapi J10, Margay J4): Eagle mills 0.6 x 1.7 at the rear pair and 0.6 x 1.2 at the front pair, "
   "as fabricated (Okapi_2024-11-02 profile.gbr); GCT's drawing (USB4105, 4 October 2019, Recommended PCB Layout) asks 0.6 x 1.70 and 0.6 x 1.40, "
   "pads 1.00 x 2.10 and 1.00 x 1.80. Andy, 2026-11-11: keep his footprint (pads 1.0 x 2.0), each slot the longer of his and GCT's, "
   "so the front pair is 1.4 (SLOT_MIN_LENGTH)"),
 'USB_MICRO_VERT_MOLEX':(('Project-Okapi/Hardware/Okapi.brd',),
   "Molex 105133-0001 vertical micro-USB shell (Okapi USB2): three milled slots, 0.5 x 1.2, 0.5 x 1.2 and 0.5 x 1.6, each around a pair of 0.5 mm drills"),
}
# a slot made longer than Eagle milled it, from the part's drawing: Eagle (x, y) of the slot center, minimum length
SLOT_MIN_LENGTH={'USB_C_CUSB31-CFM2AX-01-X':({(-4.32,2.6):1.4,(4.32,2.6):1.4},
   "GCT USB4105 drawing (4 October 2019): front pair 0.6 x 1.40 where Eagle milled 1.2; the longer slot takes stakes of either length (Andy, 2026-11-11)")}
import math
def eagle_slots(path,pkg):
    """The closed layer-46 outlines of an Eagle package as (cx, cy, length, width, axis) in Eagle coordinates (y up)."""
    p=[q for q in ET.parse(os.path.join(ws,path)).getroot().iter('package') if q.get('name')==pkg]; assert len(p)>=1,(path,pkg)
    wires=[w for w in p[0] if w.tag=='wire' and w.get('layer')=='46']; assert wires,(path,pkg,'no layer-46 wires')
    def pts(w):
        x1,y1,x2,y2=(float(w.get(k)) for k in ('x1','y1','x2','y2')); a=float(w.get('curve','0'))
        if not a: return [(x1,y1),(x2,y2)]
        c=math.hypot(x2-x1,y2-y1); r=c/(2*math.sin(math.radians(abs(a))/2)); mx,my=(x1+x2)/2,(y1+y2)/2
        h=math.sqrt(max(r*r-c*c/4,0)); s=1 if a>0 else -1   # the center is to the left of the chord for a counterclockwise arc
        cx,cy=mx-s*h*(y2-y1)/c,my+s*h*(x2-x1)/c; t0=math.atan2(y1-cy,x1-cx)
        return [(cx+r*math.cos(t0+math.radians(a)*k/64),cy+r*math.sin(t0+math.radians(a)*k/64)) for k in range(65)]
    key=lambda q:(round(q[0],4),round(q[1],4))
    left=list(wires); out=[]
    while left:   # chain wires end to end into closed loops
        loop=[left.pop(0)]; ends=[key((float(loop[0].get('x1')),float(loop[0].get('y1')))),key((float(loop[0].get('x2')),float(loop[0].get('y2'))))]
        while ends[0]!=ends[-1]:
            nxt=[w for w in left if ends[-1] in (key((float(w.get('x1')),float(w.get('y1')))),key((float(w.get('x2')),float(w.get('y2')))))]
            assert nxt,(path,pkg,'open layer-46 outline at',ends[-1]); w=nxt[0]; left.remove(w); loop.append(w)
            a,b=key((float(w.get('x1')),float(w.get('y1')))),key((float(w.get('x2')),float(w.get('y2')))); ends.append(b if a==ends[-1] else a)
        xs,ys=zip(*[q for w in loop for q in pts(w)]); x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
        assert abs(sum(abs(float(w.get('curve','0'))) for w in loop)-360)<1e-6,(path,pkg,'not a stadium: arcs')
        axis='x' if x1-x0>=y1-y0 else 'y'
        for w in loop:   # the straight sides run along the long axis
            if not w.get('curve'): assert (w.get('y1')==w.get('y2')) if axis=='x' else (w.get('x1')==w.get('x2')),(path,pkg,'not a stadium: side')
        out.append((round((x0+x1)/2,4),round((y0+y1)/2,4),round(max(x1-x0,y1-y0),4),round(min(x1-x0,y1-y0),4),axis))
    return sorted(out)
nslot=0; slot_notes={}
PADBLK=re.compile(r'^\t\(pad "([^"]*)" thru_hole (\w+)\n\t\t\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)\n\t\t\(size ([\d.]+) ([\d.]+)\)\n\t\t\(drill ([\d.]+)\)\n(?:.*\n)*?\t\)\n',re.M)
for name,(files,why) in MILLED_SLOTS.items():
    slots=eagle_slots(files[0],name)
    for f in files[1:]: assert eagle_slots(f,name)==slots,(name,f,'slots differ between Eagle files')
    if name in SLOT_MIN_LENGTH:
        mins,mwhy=SLOT_MIN_LENGTH[name]; found=0
        for k,(cx,cy,L,W,axis) in enumerate(slots):
            if (cx,cy) in mins and mins[(cx,cy)]>L: slots[k]=(cx,cy,mins[(cx,cy)],W,axis); found+=1
        assert found==len(mins),(name,'slot centers not found',mins)
        coll.append(f'| {name} | footprint | slots lengthened | – | '+', '.join(f'({x}, {y}) to {v}' for (x,y),v in mins.items())+f': {mwhy} |')
    t=fps[name]; notes=[]
    for cx,cy,L,W,axis in slots:
        ky=-cy   # a footprint's y axis points down
        sx,sy=(L,W) if axis=='x' else (W,L)
        inside=[m for m in PADBLK.finditer(t) if abs(float(m.group(3))-cx)<=sx/2+1e-6 and abs(float(m.group(4))-ky)<=sy/2+1e-6]
        assert inside,(name,cx,cy,'no pad drill inside the slot'); assert len({m.group(1) for m in inside})==1,(name,cx,cy,'pads of several numbers in one slot')
        for m in inside: assert float(m.group(8))<=W+1e-6,(name,m.group(1),'drill wider than the slot')
        if len(inside)==1 and inside[0].group(2)=='oval':
            m=inside[0]; rot=float(m.group(5) or 0); px,py=float(m.group(6)),float(m.group(7))
            assert abs(float(m.group(3))-cx)<1e-6 and abs(float(m.group(4))-ky)<1e-6,(name,m.group(1),'slot not centered on its pad')
            dx,dy=(sx,sy) if rot%180==0 else (sy,sx)   # the drill is given in the pad's own frame, as its size is
            assert px>=dx-1e-6 and py>=dy-1e-6,(name,m.group(1),'copper smaller than the slot')
            blk=m.group(0).replace('\t\t(drill %s)\n'%m.group(8),'\t\t(drill oval %s %s)\n'%(fmt6(dx),fmt6(dy)),1)
            t=t.replace(m.group(0),blk,1); ring=(min(px,py)-min(dx,dy))/2,(max(px,py)-max(dx,dy))/2
        else:   # a pair (or more) of round drills: the copper they and their bar cover is one stadium along the slot
            ext=[]
            for m in inside:
                x,y,d=float(m.group(3)),float(m.group(4)),float(m.group(6)); assert m.group(2) in ('circle','custom') and m.group(6)==m.group(7),(name,m.group(1))
                ext.append((x-d/2,x+d/2,y-d/2,y+d/2))
                for (a1,b1,a2,b2,w) in re.findall(r'\(gr_line\n\t+\(start (-?[\d.]+) (-?[\d.]+)\)\n\t+\(end (-?[\d.]+) (-?[\d.]+)\)\n\t+\(width ([\d.]+)\)',m.group(0)):
                    w=float(w); assert abs(w-d)<1e-6,(name,m.group(1),'bar narrower than the pad: the copper is not a stadium')
                    for qx,qy in ((float(a1),float(b1)),(float(a2),float(b2))): ext.append((x+qx-w/2,x+qx+w/2,y+qy-w/2,y+qy+w/2))
            X0,X1,Y0,Y1=min(e[0] for e in ext),max(e[1] for e in ext),min(e[2] for e in ext),max(e[3] for e in ext)
            px,py=X1-X0,Y1-Y0; assert abs((X0+X1)/2-cx)<1e-6 and abs((Y0+Y1)/2-ky)<1e-6,(name,'slot not centered on its copper')
            assert px>=sx-1e-6 and py>=sy-1e-6,(name,'copper smaller than the slot')
            first=inside[0]; blk=first.group(0)
            blk=re.sub(r'^\t\(pad "([^"]*)" thru_hole \w+\n\t\t\(at [^)]*\)\n\t\t\(size [^)]*\)\n\t\t\(drill [^)]*\)\n',lambda q:'\t(pad "%s" thru_hole oval\n\t\t(at %s %s)\n\t\t(size %s %s)\n\t\t(drill oval %s %s)\n'%(q.group(1),fmt6(cx),fmt6(ky),fmt6(px),fmt6(py),fmt6(sx),fmt6(sy)),blk,count=1,flags=re.M)
            blk=re.sub(r'^\t\t\(options\n(?:.*\n)*?\t\t\)\n','',blk,count=1,flags=re.M); blk=re.sub(r'^\t\t\(primitives\n(?:.*\n)*?\t\t\)\n','',blk,count=1,flags=re.M)
            t=t.replace(first.group(0),blk,1)
            for m in inside[1:]: t=t.replace(m.group(0),'',1)
            ring=(min(px,py)-W)/2,(max(px,py)-L)/2
        nslot+=1; notes.append('%s %sx%s at (%s, %s) in %sx%s copper, ring %s across and %s at the ends'%(inside[0].group(1),fmt6(W),fmt6(L),fmt6(cx),fmt6(ky),fmt6(min(px,py)),fmt6(max(px,py)),fmt6(ring[0]),fmt6(ring[1])))
    fps[name]=t; slot_notes[name]=notes
    coll.append(f'| {name} | footprint | {len(slots)} milled slots | – | oval drills from Eagle layer 46: {"; ".join(notes)}. {why} |')
MARGIN=re.compile(r'^\t\t\((?:solder_mask_margin|solder_paste_margin) -?[\d.]+\)\n',re.M)
# a courtyard for a footprint that came from Eagle without one: the rectangle 'margin' beyond the union of the body
# (F.Fab) and every pad, rounded outward to 0.01 mm (Andy, 2026-11-11: the standard courtyard)
COURTYARD={'USB_C_CUSB31-CFM2AX-01-X':(0.25,"USB-C receptacle (Okapi J10, Margay J4): Eagle drew no tKeepout")}
import uuid as _uuid2, math as _m
for name,(margin,why) in COURTYARD.items():
    t=fps[name]; assert '"F.CrtYd"' not in t,(name,'already has a courtyard')
    xs=[];ys=[]
    for m in re.finditer(r'^\t\((fp_line|fp_poly|fp_arc|fp_rect)\n(.*?)\n\t\)',t,re.S|re.M):
        if '(layer "F.Fab")' in m.group(2):
            for x,y in re.findall(r'\((?:start|end|mid|xy) (-?[\d.]+) (-?[\d.]+)\)',m.group(2)): xs.append(float(x)); ys.append(float(y))
    assert xs,(name,'no F.Fab outline')
    for m in re.finditer(r'\(pad "[^"]*" \w+ \w+\n\t\t\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)\n\t\t\(size ([\d.]+) ([\d.]+)\)',t):
        x,y,r,w,h=float(m.group(1)),float(m.group(2)),float(m.group(3) or 0),float(m.group(4)),float(m.group(5))
        assert r%90==0,(name,'pad rotation not a multiple of 90')
        if r%180==90: w,h=h,w
        xs+=[x-w/2,x+w/2]; ys+=[y-h/2,y+h/2]
    lo=lambda v:_m.floor(round((v-margin)*100,6))/100; hi=lambda v:_m.ceil(round((v+margin)*100,6))/100
    x0,y0,x1,y1=lo(min(xs)),lo(min(ys)),hi(max(xs)),hi(max(ys))
    rect=('\t(fp_rect\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n'
          '\t\t(layer "F.CrtYd")\n\t\t(uuid "%s")\n\t)\n')%(fmt6(x0),fmt6(y0),fmt6(x1),fmt6(y1),_uuid2.uuid5(_uuid2.NAMESPACE_URL,'nw-cold-silicon:%s:courtyard'%name))
    i=t.index('\t(pad '); fps[name]=t[:i]+rect+t[i:]
    coll.append(f'| {name} | footprint | courtyard | – | F.CrtYd rectangle ({fmt6(x0)}, {fmt6(y0)}) to ({fmt6(x1)}, {fmt6(y1)}), {margin} mm beyond body and pads: {why} |')
# a footprint's description where its Eagle package had none, or where its design intent must travel with it
FP_DESCR={'USB_C_CUSB31-CFM2AX-01-X':"USB 2.0 Type-C receptacle, 16 contacts, top mount, horizontal. Laid out by Andy Wickert (Project-Margay 364c9ef, 2022) "
   "to fit both the CUI (Same Sky) CUSB31-CFM2AX-01-X and the GCT USB4105-GF-A (Andy, 2026-11-11). Shell slots 0.6 x 1.7 mm (rear) and "
   "0.6 x 1.4 mm (front), each the longer of Andy's layout and GCT's drawing; courtyard 0.25 mm beyond body and pads."}
for name,text in FP_DESCR.items():
    t=fps[name]; t=re.sub(r'^\t\(descr "[^"]*"\)\n','',t,flags=re.M)
    t,n=re.subn(r'^\t\(layer "F\.Cu"\)\n',lambda m:m.group(0)+'\t(descr "%s")\n'%text.replace('"',"'"),t,count=1,flags=re.M); assert n==1,name
    fps[name]=t; coll.append(f'| {name} | footprint | descr | – | {text} |')
# Eagle's documentation layers printed: the CAM job of every Northern Widget board put tDocu (51) on the top
# silkscreen and bDocu (52) on the bottom (Okapi_2024-11-02, Margay's 2023 fab), so a package's pin stripes, outlines
# and diagrams were on the boards. The converter puts them on F.Fab and B.Fab, which do not print, and they are the
# only Fab items it writes (checked per package on both boards). Each is kept on Fab, for the assembly drawing, and
# copied to the silkscreen of its side (Andy, 2026-11-13: every mark that printed prints).
FAB_ITEM=re.compile(r'^\t\((fp_line|fp_arc|fp_circle|fp_rect|fp_poly|fp_text)\b.*?\n\t\)\n',re.S|re.M)
ndocu=0
for name in list(fps):
    t=fps[name]; copies=[]
    for m in FAB_ITEM.finditer(t):
        for fab,silk in (('"F.Fab"','"F.SilkS"'),('"B.Fab"','"B.SilkS"')):
            if '\t\t(layer %s)'%fab in m.group(0) or '\t\t(layer %s knockout)'%fab in m.group(0):
                copies.append(m.group(0).replace('(layer %s'%fab,'(layer %s'%silk,1))
    if not copies: continue
    i=t.index('\t(pad ') if '\t(pad ' in t else t.rindex('\t(embedded_fonts')
    fps[name]=t[:i]+''.join(copies)+t[i:]; ndocu+=1
# native footprints: drawn in KiCad, not converted from an Eagle library (native/*.kicad_mod)
nnative=0; native_names=[]
for f in sorted(glob.glob(os.path.join(REPO,'native','*.kicad_mod'))):
    name=os.path.basename(f)[:-len('.kicad_mod')]
    assert name not in fps,('native footprint name collides with a converted one',name)
    fps[name]=open(f).read(); nnative+=1; native_names.append(name)
nmargin=0
for name,t in fps.items():
    t,nm=MARGIN.subn('',t); nmargin+=nm   # no per-pad mask or paste margin: the board's design rules set them
    k=iter(range(10**6))
    t=re.sub(r'\(uuid "[^"]+"\)',lambda m:'(uuid "%s")'%uuid.uuid5(uuid.NAMESPACE_URL,'%s/%s/%d'%(LIB,name,next(k))),t)
    open(os.path.join(PRETTY,name+'.kicad_mod'),'w').write(t)
SYM_OUT=SYM; SYM=os.path.join(REPO,LIB+'.building.kicad_sym')
open(SYM,'w').write(head+''.join(syms[n] for n in sorted(syms))+')\n')
rc,o=run(['kicad-cli','fp','upgrade','--force',PRETTY]); assert rc==0,o
rc,o=run(['kicad-cli','sym','upgrade','--force',SYM]); assert rc==0,o
# idempotence: a second pass must change nothing
p2=os.path.join(tmp,'p2'); shutil.copytree(PRETTY,p2); run(['kicad-cli','fp','upgrade','--force',p2])
s2=os.path.join(tmp,'s2.kicad_sym'); shutil.copy(SYM,s2); run(['kicad-cli','sym','upgrade','--force',s2])
chg=sum(1 for f in os.listdir(PRETTY) if open(os.path.join(PRETTY,f)).read()!=open(os.path.join(p2,f)).read())
same=open(SYM).read()==open(s2).read()
prov+=['',f'Artwork (logos, {ngr} footprints and symbols): reference LOGO, excluded from the BOM, the position files and simulation, with a description.',f'Through-hole pads grown to Eagle\'s restring ({nrestring}): drill + 2 x max(25 % of the drill, 5 mil), the ring Eagle fabricated whatever the package drew.',f'Milled slots from Eagle layer 46 ({nslot}, in '+', '.join('`%s`'%n for n in slot_notes)+'): KiCad\'s Eagle reader ignores the Milling layer, so each outline around a pad\'s drill becomes that pad\'s oval drill (COLLISIONS.md gives each slot and its ring).','Eagle restricts as converted: tRestrict a no-copper keepout on F.Cu, bRestrict on B.Cu, vRestrict a via-only keepout on every copper layer; a restrict drawn as wires becomes the polygon they enclose ('+', '.join(WIRE_RESTRICTS)+').',f'Eagle tDocu and bDocu copied from F.Fab and B.Fab to the silkscreen of their side ({ndocu} footprints): the Northern Widget boards printed them.',f'No footprint carries a per-pad solder-mask or paste margin ({nmargin} removed): the converter had written KiCad\'s 4 mil default where Eagle\'s design rules on every Northern Widget board set a 2.5 mil stop frame, and in KiCad that is the board\'s pad-to-mask clearance, not the footprint\'s.',f'Library: **{len(fps)} footprints** in `{LIB}.pretty`, **{len(syms)} symbols** in `{LIB}.kicad_sym`.',
       f'Native footprints, drawn in KiCad and copied from native/ ({nnative}): '+(', '.join('`%s`'%n for n in native_names) or 'none')+'; each names its source in its descr.',
       f'Second pass of kicad-cli upgrade on the output: {chg} footprint files changed, symbol file {"identical" if same else "CHANGED"}.',
       '','Rule: precedence is the order of the table; identical content is kept once; differing content from a PRIMARY source is kept as NAME_key; an EXTRAS source adds only names absent so far. See COLLISIONS.md.']
open(os.path.join(REPO,'PROVENANCE.md'),'w').write('\n'.join(prov)+'\n')
open(os.path.join(REPO,'COLLISIONS.md'),'w').write('\n'.join(coll)+'\n')
assert chg==0 and same, ('second pass changed the output',chg,same)
if os.path.isdir(PRETTY_OUT): shutil.rmtree(PRETTY_OUT)
os.rename(PRETTY,PRETTY_OUT); os.replace(SYM,SYM_OUT); PRETTY,SYM=PRETTY_OUT,SYM_OUT
print(f'{len(fps)} footprints, {len(syms)} symbols; second pass: {chg} fp changed, sym {"identical" if same else "CHANGED"}; collisions {len(coll)-6}')
shutil.rmtree(tmp)
