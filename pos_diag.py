# -*- coding: utf-8 -*-
"""على أخطاء BERT الفعليّة (مقابل الذهبيّ): هل الصوابُ موجودٌ في قراءات CAMeL؟ وما وسمُه (اسم/فعل)؟"""
import sys, os, random
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
N=int(os.environ.get("BENCH_N","400"))
print(f"… تحميل النموذج + محلّل CAMeL (عيّنة={N})")
import app_teach as A
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_snap import _norm, _strip
from data.vocab_v2 import strip_diacritics
an=Analyzer(MorphologyDB.builtin_db())
lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(13).shuffle(lines); lines=lines[:N]
cat={"اسمٌ_صوابُه_متاح":0,"فعلٌ_صوابُه_متاح":0,"صوابٌ_غيرُ_متاح":0}; err=0; ex=[]
for gold in lines:
    pb=A.INF.diacritize(strip_diacritics(gold))
    gws=gold.split(" "); pws=pb.split(" ")
    if len(gws)!=len(pws): continue
    for gw,pw in zip(gws,pws):
        if _norm(gw)==_norm(pw): continue
        err+=1
        try: analyses=an.analyze(_strip(pw))
        except Exception: analyses=[]
        norms={}
        for a in analyses:
            norms.setdefault(_norm(a.get('diac','')), a.get('pos',''))
        gn=_norm(gw)
        if gn in norms:
            pos=norms[gn]
            if pos=="verb": cat["فعلٌ_صوابُه_متاح"]+=1; tag="فعل:"+pos
            else: cat["اسمٌ_صوابُه_متاح"]+=1; tag="اسم:"+pos
        else:
            cat["صوابٌ_غيرُ_متاح"]+=1; tag="غير متاح"
        if len(ex)<22: ex.append((gw,pw,tag))
print("="*60)
print(f"إجماليّ أخطاء BERT في العيّنة: {err}")
for k,v in cat.items():
    print(f"  {k:<22}: {v}  ({100*v/max(err,1):.1f}%)")
print("="*60)
print("أمثلة (الذهبيّ | BERT | تصنيف):")
for gw,pw,tag in ex:
    print(f"   {gw:<16} | {pw:<16} | {tag}")
print("="*60)
