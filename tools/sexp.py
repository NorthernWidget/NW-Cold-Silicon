"""Minimal reader for KiCad s-expression files (.kicad_sch, .kicad_pcb, .kicad_sym).

parse(text) returns nested lists; kids(node, key) and kid(node, key) walk them.
"""
def parse(txt):
    i=0;n=len(txt);stack=[[]]
    while i<n:
        c=txt[i]
        if c=='(':
            stack.append([]); i+=1
        elif c==')':
            l=stack.pop(); stack[-1].append(l); i+=1
        elif c=='"':
            j=i+1; s=[]
            while txt[j]!='"':
                if txt[j]=='\\': s.append(txt[j+1]); j+=2
                else: s.append(txt[j]); j+=1
            stack[-1].append(''.join(s)); i=j+1
        elif c.isspace(): i+=1
        else:
            j=i
            while j<n and not txt[j].isspace() and txt[j] not in '()': j+=1
            stack[-1].append(txt[i:j]); i=j
    return stack[0][0]
def kids(node,key): return [x for x in node if isinstance(x,list) and x and x[0]==key]
def kid(node,key,default=None):
    k=kids(node,key); return k[0] if k else default
