# -*- coding: utf-8 -*-
"""أسوأُ أسطرِ الأخبارِ لنموذجِك (تشكيلٌ كامل) — لكشفِ سببِ ارتفاعِ DER."""
import os,sys
BASE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,BASE); sys.path.insert(0,os.path.join(BASE,"scripts"))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import re
from data.vocab_v2 import split_letters_and_diacritics as SPLIT
_H=set("ًٌٍَُِّْٰ")
_K=re.compile(r"[^ؠ-ٰٟ ]")
def bare(s): return "".join(c for c in s if c not in _H)
def norm(s): return re.sub(r"\s+"," ",_K.sub("",s)).strip()
def der1(g,p):
    Lg,Cg=SPLIT(g); Lp,Cp=SPLIT(p)
    if len(Lg)!=len(Lp): return None,len(Lg)
    t=e=0
    for i in range(len(Lg)):
        if Lg[i]==" ": continue
        t+=1
        if int(Cg[i])!=int(Cp[i]): e+=1
    return (100*e/max(1,t)), t
import diac_pipeline
N=int(os.environ.get("N_NEWS","150"))
gold=[l.strip() for l in open("data/news_gold_clean.txt",encoding="utf-8") if l.strip()][:N]
rows=[]
for i,g in enumerate(gold):
    b=diac_pipeline.diacritize(bare(g), False)[0] or bare(g)
    gN,bN=norm(g),norm(b)
    d,t=der1(gN,bN)
    bare_out = (sum(1 for c in b if c in _H)==0)   # عاد بلا تشكيل؟
    rows.append((d,t,len(bare(g)),bare_out,g[:70],b[:70]))
    if (i+1)%50==0: print(f"  {i+1}/{len(gold)}",flush=True)
ok=[r for r in rows if r[0] is not None]
skip=[r for r in rows if r[0] is None]
bare_lines=[r for r in rows if r[3]]
print(f"\nأسطر={len(rows)} · متخطّى(طول)={len(skip)} · عادت بلا تشكيل={len(bare_lines)}")
print("=== أسوأ 8 أسطر (DER%، طول، باراي) ===")
for d,t,ln,bo,gg,bb in sorted(ok,key=lambda r:-r[0])[:8]:
    print(f"DER={d:5.1f}% طول={ln:4d} بلا_تشكيل={bo}\n  ذهبيّ: {gg}\n  BERT : {bb}")
if bare_lines:
    print("\n=== أمثلةُ أسطرٍ عادت بلا تشكيل (أطول) ===")
    for d,t,ln,bo,gg,bb in sorted(bare_lines,key=lambda r:-r[2])[:3]:
        print(f"طول={ln}\n  ذهبيّ: {gg}\n  BERT : {bb}")
