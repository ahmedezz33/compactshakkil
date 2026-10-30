# -*- coding: utf-8 -*-
"""قلبُ المنهجيّة: BERT أساسٌ، وCAMeL يتدخّلُ فقط في «المشكوكِ فيه».
«المشكوك» = صورةُ BERT غيرُ جائزةٍ صرفيًّا (ليست ضمنَ تحليلاتِ CAMeL بعد تحييدِ الاصطلاح).
سياستان: (SAFE) نتدخّلُ فقط إن حسمَ CAMeL يقينًا (صورةٌ جائزةٌ واحدة)؛
          (SNAP) نأخذُ أقربَ صورةٍ جائزة. المحلّلُ وحدَه بلا MLE، قياسٌ عادلٌ مُحيَّد."""
import sys, os, random, functools, io, re
N=int(os.environ.get("BENCH_N","3000")); OUT="eval_report_bertfirst.txt"
buf=io.StringIO()
def P(*a):
    s=" ".join(str(x) for x in a); print(s); buf.write(s+"\n")
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
P(f"… BERT أساسٌ + CAMeL للمشكوك — عيّنة={N}")
import app_teach as A
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_snap import _norm, _strip
from data.vocab_v2 import strip_diacritics
an=Analyzer(MorphologyDB.builtin_db())

_WAQF=re.compile(r'[ًٌٍَُِ]([اوىي]?)$')
def _conv(s):
    s=_WAQF.sub(r'\1', s).replace('ٰ','')
    s=re.sub(r'َ(?=ا)','',s); s=re.sub(r'ِ(?=ي)','',s); s=re.sub(r'ُ(?=و)','',s)
    return s
def _lev(a,b):
    m,n=len(a),len(b)
    if not m: return n
    if not n: return m
    prev=list(range(n+1))
    for i in range(1,m+1):
        cur=[i]+[0]*n; ai=a[i-1]
        for j in range(1,n+1):
            cur[j]=min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ai!=b[j-1]))
        prev=cur
    return prev[n]
@functools.lru_cache(maxsize=400000)
def _analyses(bare):
    try: raw=tuple(sorted({a['diac'] for a in an.analyze(bare) if a.get('diac')}))
    except Exception: raw=tuple()
    keys=frozenset(_conv(_norm(x)) for x in raw)
    return raw, keys

lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(13).shuffle(lines); lines=lines[:N]
tot=0; skip=0; e_bert=0; e_safe=0; e_snap=0
safe_fire=0; safe_fix=0; safe_break=0
snap_fire=0; snap_fix=0; snap_break=0
ex_safe=[]; ex_snap=[]
for gold in lines:
    gws=gold.split(" ")
    pb=A.INF.diacritize(strip_diacritics(gold)); pws=pb.split(" ")
    if len(pws)!=len(gws): skip+=1; continue
    tot+=len(gws)
    for i,gw in enumerate(gws):
        bare=_strip(pws[i]); gK=_conv(_norm(gw)); bK=_conv(_norm(pws[i]))
        raw,keys=_analyses(bare)
        illegal = bool(keys) and (bK not in keys)
        # SAFE
        safe=bK
        if illegal and len(keys)==1:
            safe=next(iter(keys)); safe_fire+=1
            if safe==gK and bK!=gK: safe_fix+=1
            elif safe!=gK and bK==gK: safe_break+=1
            if len(ex_safe)<16: ex_safe.append((gw,pws[i],next(iter(raw))))
        # SNAP
        snap=bK
        if illegal:
            best=min(raw,key=lambda r:_lev(r,pws[i])) if raw else None
            if best is not None:
                snap=_conv(_norm(best)); snap_fire+=1
                if snap==gK and bK!=gK: snap_fix+=1
                elif snap!=gK and bK==gK: snap_break+=1
                if len(ex_snap)<16: ex_snap.append((gw,pws[i],best))
        if gK!=bK: e_bert+=1
        if gK!=safe: e_safe+=1
        if gK!=snap: e_snap+=1
def pc(x,d): return f"{100*x/max(d,1):.2f}%"
P("="*70)
P(f"كلماتٌ مُقيَّمة: {tot}   [قياسٌ عادلٌ مُحيَّدٌ من الاصطلاح]")
P("="*70)
P("معدّلُ الخطأِ (أقلُّ=أفضل):")
P(f"  BERT وحدَه                                 : {e_bert:5d}  ({pc(e_bert,tot)})")
P(f"  BERT + CAMeL للمشكوك (SAFE: غير‑جائز+حسمٌ يقينيّ): {e_safe:5d}  ({pc(e_safe,tot)})   صافٍ {e_bert-e_safe:+d}")
P(f"  BERT + CAMeL للمشكوك (SNAP: غير‑جائز+أقرب جائز)  : {e_snap:5d}  ({pc(e_snap,tot)})   صافٍ {e_bert-e_snap:+d}")
P("-"*70)
P(f"SAFE: تدخّلَ {safe_fire} مرّة — أصلحَ {safe_fix} · أفسدَ {safe_break}  (صافٍ {safe_fix-safe_break:+d})")
P(f"SNAP: تدخّلَ {snap_fire} مرّة — أصلحَ {snap_fix} · أفسدَ {snap_break}  (صافٍ {snap_fix-snap_break:+d})")
P("="*70)
P("أمثلةُ تدخّلِ SAFE (الذهبيّ | BERT | حسمُ CAMeL):")
for a,b,c in ex_safe: P(f"   {a:<18} | {b:<18} | {c}")
P("\nأمثلةُ تدخّلِ SNAP (الذهبيّ | BERT | أقربُ جائز):")
for a,b,c in ex_snap: P(f"   {a:<18} | {b:<18} | {c}")
P("="*70)
open(OUT,"w",encoding="utf-8").write(buf.getvalue())
print(f"\n[كُتِبَ إلى {OUT}]")
