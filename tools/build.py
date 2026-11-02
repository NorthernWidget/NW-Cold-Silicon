"""Build nw-cold-silicon.pretty and nw-cold-silicon.kicad_sym from the Eagle libraries.

usage: build.py [--upto KEY] [--workspace DIR]

Converts each source library with kicad-cli (fp upgrade -o, sym upgrade -o),
then merges them in the precedence order of SOURCES. A name that appears in two
sources with identical content (uuid lines ignored) is kept once. A name whose
content differs is kept from the earlier source under its own name and from a
later PRIMARY source under NAME_<key>, so nothing is lost; from an EXTRAS source
(an older fork or copy) only names absent so far are added. Every symbol's Footprint field is
rewritten from the Eagle library name to nw-cold-silicon and to the merged
footprint name, since the merged library has one nickname. Two symbols that
differ only in their Description property count as identical and the earlier
one is kept (a description is neither geometry nor connectivity); COLLISIONS.md
says so for each. The script writes PROVENANCE.md and COLLISIONS.md itself, so
every number in them is the build's.
--upto stops after the named source, for one commit per source.
"""
import os,re,sys,shutil,subprocess,tempfile,uuid,datetime,collections
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
EAGLE_KEY={'bschulz_passives':'passives','bschulz':'bschulz','awickert':'awickert','csandell':'csandell'}
LIB='nw-cold-silicon'; PRETTY=os.path.join(REPO,LIB+'.pretty'); SYM=os.path.join(REPO,LIB+'.kicad_sym')
def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True); return p.returncode,(p.stdout+p.stderr).strip()
def git(path,*a):
    return subprocess.run(['git','-C',os.path.dirname(path)]+list(a),capture_output=True,text=True).stdout.strip()
def norm(t): return re.sub(r'\n\s*\(uuid "[^"]+"\)','',t)
def nodesc(t): return re.sub(r'\t\t\(property "Description" "(?:[^"\\]|\\.)*"','',t)
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
        if name not in fps: fps[name]=t; fpsrc[name]=key; continue
        if norm(fps[name])==norm(t): coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | kept once |'); continue
        if kind=='PRIMARY':
            new=f'{name}_{key}'; fps[new]=t.replace(f'(footprint "{name}"',f'(footprint "{new}"',1); fpsrc[new]=key; fpmap[key][name]=new
            coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | both: `{new}` |')
        else: coll.append(f'| {name} | footprint | {fpsrc[name]} | {key} | older copy skipped |')
    h,blocks=split_syms(open(d+'.kicad_sym').read()); head=head or h
    for name,b in blocks.items():
        nsy+=1; b=refoot(b,fpmap.get(key,{}))
        if name not in syms: syms[name]=b; symsrc[name]=key; continue
        if syms[name]==b: coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | kept once |'); continue
        if nodesc(syms[name])==nodesc(b): coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | kept once, description differs |'); continue
        if kind=='PRIMARY':
            new=f'{name}_{key}'; syms[new]=rename_sym(b,name,new); symsrc[new]=key
            coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | both: `{new}` |')
        else: coll.append(f'| {name} | symbol | {symsrc[name]} | {key} | older copy skipped |')
    prov.append(f'| {key} | {kind} | `{rel}` | {git(src,"log","-1","--format=%h %cs","--",os.path.basename(src))} | {npk} | {nsy} | {"; ".join(warn) or "–"} |')
if not upto:
    prov+=['','## Boards','','Footprints embedded in the KiCad boards, each matched to the library through its element\'s Eagle library of origin. A name no source library holds is added from the Eagle board\'s own package definition through `kicad-cli pcb import`, the converter that built the rest. Columns: identical to the library copy in pads and graphics; same pads but the KiCad board\'s copy (a June 2026 import) draws the graphics or sizes a non-plated hole differently; pads differ (the board copy is NOT taken over; COLLISIONS.md lists it); unchecked means the board has no front-side instance to compare.','',
           '| board | file | embedded names | identical | pads identical | pads differ | added | unchecked |','|---|---|---|---|---|---|---|---|']
    for bkey,pcb,brd in BOARDS:
        el={e.get('name'):(e.get('library'),e.get('package')) for e in ET.parse(os.path.join(ws,brd)).getroot().iter('element')}
        up=os.path.join(tmp,'brd',bkey+'.kicad_pcb'); os.makedirs(os.path.dirname(up),exist_ok=True); shutil.copy(os.path.join(ws,pcb),up)
        rc,o=run(['kicad-cli','pcb','upgrade','--force',up]); assert rc==0,o   # older boards use another layout
        emb=embedded(up); n_id=n_pad=n_dif=n_add=n_unc=0
        for full,insts in sorted(emb.items()):
            n=full.split(':')[-1].replace('_528','')
            groups=collections.defaultdict(list)
            for b in insts:
                ref=re.search(r'\(property "Reference" "([^"]*)"',b).group(1); groups[el.get(ref,(None,None))[0]].append(b)
            for lib,ins in groups.items():
                key=EAGLE_KEY.get(lib); merged=fpmap.get(key,{}).get(n) if key else None
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
    prov+=['','Added from the boards:','']+[f'- `{n}`: {NOTES.get(n,"no note")}' for n in sorted(k for k,v in fpsrc.items() if v.startswith('board:'))]
if os.path.isdir(PRETTY): shutil.rmtree(PRETTY)
os.makedirs(PRETTY)
for name,t in fps.items():
    k=iter(range(10**6))
    t=re.sub(r'\(uuid "[^"]+"\)',lambda m:'(uuid "%s")'%uuid.uuid5(uuid.NAMESPACE_URL,'%s/%s/%d'%(LIB,name,next(k))),t)
    open(os.path.join(PRETTY,name+'.kicad_mod'),'w').write(t)
open(SYM,'w').write(head+''.join(syms[n] for n in sorted(syms))+')\n')
rc,o=run(['kicad-cli','fp','upgrade','--force',PRETTY]); assert rc==0,o
rc,o=run(['kicad-cli','sym','upgrade','--force',SYM]); assert rc==0,o
# idempotence: a second pass must change nothing
p2=os.path.join(tmp,'p2'); shutil.copytree(PRETTY,p2); run(['kicad-cli','fp','upgrade','--force',p2])
s2=os.path.join(tmp,'s2.kicad_sym'); shutil.copy(SYM,s2); run(['kicad-cli','sym','upgrade','--force',s2])
chg=sum(1 for f in os.listdir(PRETTY) if open(os.path.join(PRETTY,f)).read()!=open(os.path.join(p2,f)).read())
same=open(SYM).read()==open(s2).read()
prov+=['',f'Library: **{len(fps)} footprints** in `{LIB}.pretty`, **{len(syms)} symbols** in `{LIB}.kicad_sym`.',
       f'Second pass of kicad-cli upgrade on the output: {chg} footprint files changed, symbol file {"identical" if same else "CHANGED"}.',
       '','Rule: precedence is the order of the table; identical content is kept once; differing content from a PRIMARY source is kept as NAME_key; an EXTRAS source adds only names absent so far. See COLLISIONS.md.']
open(os.path.join(REPO,'PROVENANCE.md'),'w').write('\n'.join(prov)+'\n')
open(os.path.join(REPO,'COLLISIONS.md'),'w').write('\n'.join(coll)+'\n')
assert chg==0 and same, ('second pass changed the output',chg,same)
print(f'{len(fps)} footprints, {len(syms)} symbols; second pass: {chg} fp changed, sym {"identical" if same else "CHANGED"}; collisions {len(coll)-6}')
shutil.rmtree(tmp)
