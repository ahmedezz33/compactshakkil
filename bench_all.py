# -*- coding: utf-8 -*-
import sys, os, random
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
N=int(os.environ.get("BENCH_N","400")); SEED=13
print(f"… تحميل النموذج + CAMeL (عيّنة={N})")
import app_teach as A, camel_snap, gazetteer
from camel_snap import _norm as _CN
from data.vocab_v2 import split_letters_and_diacritics as SPL, strip_diacritics
INF=A.INF
lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(SEED).shuffle(lines); lines=lines[:N]
def der(g,p):
    _,gd=SPL(g); _,pd=SPL(p); n=min(len(gd),len(pd))
    return sum(1 for i in range(n) if gd[i]!=pd[i])+abs(len(gd)-len(pd)), max(len(gd),1)
CFG={"BERT":lambda d:d,
     "BERT+fill":camel_snap.fill_text,
     "BERT+gaz":gazetteer.apply_text,
     "BERT+fill+gaz":lambda d:gazetteer.apply_text(camel_snap.fill_text(d))}
E={k:0 for k in CFG}; CH=0
for i,g in enumerate(lines):
    pb=INF.diacritize(strip_diacritics(g)); gN=_CN(g)
    for k,fn in CFG.items():
        e,t=der(gN,_CN(fn(pb))); E[k]+=e
    _,d=der(gN,_CN(pb)); CH+=d
    if (i+1)%100==0: print(f"  … {i+1}/{N}")
print("="*56)
print(f"عيّنات={len(lines)}  (DER موحَّد — التراث)")
for k in CFG: print(f"  {k:<16}: {100*E[k]/CH:.2f}%")
print("="*56)
print("جملةُ المقالِ تحتَ كلِّ مسار:")
art="خيم الحزن على مدينة المحمودية عقب وفاة عزة رمزي البالغة من العمر 28 عاما"
pb=A.diacritize(art)[0]
for k,fn in CFG.items():
    print(f"  [{k}] {fn(pb)}")
print("="*56)
