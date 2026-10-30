# -*- coding: utf-8 -*-
import sys, random
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
print("… تحميل النموذج + CAMeL")
import app_teach as A
import camel_snap
from camel_snap import _norm, _strip, _cands, snap_word
from data.vocab_v2 import strip_diacritics
INF=A.INF
lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(7).shuffle(lines); lines=lines[:15]

kept_valid=kept_prop=replaced=0; ex=[]
for gold in lines:
    bare=strip_diacritics(gold)
    pb=INF.diacritize(bare)
    for w in pb.split(" "):
        if len(_strip(w))<2: continue
        cands=_cands(_strip(w))
        if not cands:
            kept_prop+=1; continue
        if any(_norm(c)==_norm(w) for c in cands):
            kept_valid+=1; continue
        replaced+=1
        if len(ex)<18:
            best=snap_word(w)
            ex.append((w,best))
tot=kept_valid+kept_prop+replaced
print("="*60)
print(f"إجمالي الكلمات: {tot}")
print(f"  أُبقيتْ (جائزةٌ تحت الاصطلاح): {kept_valid}  ({100*kept_valid/tot:.1f}%)")
print(f"  أُبقيتْ (عَلَمٌ/لا تحليل):        {kept_prop}  ({100*kept_prop/tot:.1f}%)")
print(f"  استُبدِلَت:                      {replaced}  ({100*replaced/tot:.1f}%)")
print("="*60)
print("أمثلةٌ على المُستبدَل (BERT → snap):")
for w,b in ex:
    print(f"   {w:<18} → {b:<18}  | norm(BERT)={_norm(w)}")
print("="*60)
