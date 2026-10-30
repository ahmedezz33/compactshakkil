# -*- coding: utf-8 -*-
"""قياس DER: النموذج وحدَه مقابل النموذج+snap على عيّنةٍ من data/processed/test.txt"""
import sys, os, random
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
N=int(os.environ.get("BENCH_N","400")); SEED=int(os.environ.get("BENCH_SEED","13"))
print(f"… تحميل النموذج + CAMeL (عيّنة={N})")
import app_teach as A
import camel_snap
from camel_snap import _norm as _CNORM
from data.vocab_v2 import split_letters_and_diacritics, strip_diacritics
INF=A.INF
lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(SEED).shuffle(lines); lines=lines[:N]

def units(s):
    r=split_letters_and_diacritics(s)
    L,D=(r[0],r[1]) if isinstance(r,(list,tuple)) and len(r)>=2 else (list(s),[""]*len(s))
    return list(L),list(D)

def der(gold,pred):
    gL,gD=units(gold); pL,pD=units(pred)
    n=min(len(gD),len(pD))
    err=sum(1 for i in range(n) if gD[i]!=pD[i])+abs(len(gD)-len(pD))
    return err, max(len(gD),1)

def score(gold,pred):
    eR,tR=der(gold,pred)                       # خام (بالاصطلاح الأصليّ)
    eN,tN=der(_CNORM(gold),_CNORM(pred))        # موحَّد الاصطلاح
    return eR,tR,eN,tN,(1 if gold.strip()==pred.strip() else 0)

ebR=esR=chR=0; ebN=esN=chN=0; wb=ws=0
for i,gold in enumerate(lines):
    bare=strip_diacritics(gold)
    try: pb=INF.diacritize(bare)
    except Exception as e: print("err",e); continue
    ps=camel_snap.snap_text(pb)
    aR,tR,aN,tN,w=score(gold,pb); bR,_,bN,_,w2=score(gold,ps)
    ebR+=aR; esR+=bR; chR+=tR; ebN+=aN; esN+=bN; chN+=tN; wb+=w; ws+=w2
    if (i+1)%100==0: print(f"  … {i+1}/{len(lines)}")
print("="*56)
print(f"عيّنات={len(lines)}")
print("—— DER خام (بالاصطلاح الأصليّ) ——")
print(f"BERT      : {100*ebR/chR:.2f}%    جُمَلٌ مطابقة={100*wb/len(lines):.1f}%")
print(f"BERT+snap : {100*esR/chR:.2f}%    جُمَلٌ مطابقة={100*ws/len(lines):.1f}%")
print("—— DER باصطلاحٍ موحَّد (الأعدل للمقارنة) ——")
print(f"BERT      : {100*ebN/chN:.2f}%")
print(f"BERT+snap : {100*esN/chN:.2f}%")
dN=100*(esN-ebN)/chN
print(f"الفرق (snap، موحَّد): {'+' if dN>=0 else ''}{dN:.2f}%  →  {'أسوأ' if dN>0 else 'أفضل' if dN<0 else 'سواء'}")
print("="*56)
