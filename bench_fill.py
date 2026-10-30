# -*- coding: utf-8 -*-
import sys, os, random
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
N=int(os.environ.get("BENCH_N","400")); SEED=int(os.environ.get("BENCH_SEED","13"))
print(f"… تحميل النموذج + CAMeL (عيّنة={N})")
import app_teach as A, camel_snap
from camel_snap import _norm as _CN
from data.vocab_v2 import split_letters_and_diacritics as SPL, strip_diacritics
INF=A.INF
lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(SEED).shuffle(lines); lines=lines[:N]
def der(g,p):
    _,gd=SPL(g); _,pd=SPL(p); n=min(len(gd),len(pd))
    return sum(1 for i in range(n) if gd[i]!=pd[i])+abs(len(gd)-len(pd)), max(len(gd),1)
ebN=efN=chN=0; bare=0; lett=0
for i,g in enumerate(lines):
    pb=INF.diacritize(strip_diacritics(g))
    pf=camel_snap.fill_text(pb)
    _,d=SPL(pb); bare+=sum(1 for x in d if x==0); lett+=len(d)
    a,t=der(_CN(g),_CN(pb)); b,_=der(_CN(g),_CN(pf))
    ebN+=a; efN+=b; chN+=t
    if (i+1)%100==0: print(f"  … {i+1}/{N}")
print("="*56)
print(f"عيّنات={len(lines)}  |  حروفٌ تركها BERT فارغةً: {100*bare/lett:.1f}%  |  حروفٌ ملأها الدمج: {camel_snap._FILLED[0]}")
print(f"BERT       : DER(موحَّد)={100*ebN/chN:.2f}%")
print(f"BERT+fill  : DER(موحَّد)={100*efN/chN:.2f}%")
d=100*(efN-ebN)/chN
print(f"الفرق (fill): {'+' if d>=0 else ''}{d:.2f}%  →  {'أسوأ' if d>0 else 'أفضل' if d<0 else 'سواء'}")
print("="*56)
