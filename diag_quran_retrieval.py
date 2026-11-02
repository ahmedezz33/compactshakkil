# -*- coding: utf-8 -*-
"""هل يسترجعُ diac_pipeline الآياتِ أم يتنبّأ؟ ومتى يفشلُ البحث؟"""
import os, sys
BASE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,BASE); sys.path.insert(0,os.path.join(BASE,"scripts"))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import diac_pipeline
DAG="ٰ"
HRK=set("ًٌٍَُِّْٰ")
def bare(s): return "".join(c for c in s if c not in HRK)
ayat=[l.strip() for l in open("data/quran_gold_sample.txt",encoding="utf-8") if l.strip()][:int(os.environ.get("N","30"))]
ret=pred=0; dagger_lost=0
print("آية | المسار | خنجريّة ذهبيّ→ناتج")
for g in ayat:
    b=bare(g)
    out,route=diac_pipeline.diacritize(b, False)   # bare (كالمقياس)
    r="استرجاع" if "استرد" in route else "تنبّؤ"
    if r=="استرجاع": ret+=1
    else: pred+=1
    dg=g.count(DAG); do=out.count(DAG)
    if dg>do: dagger_lost+=1
    if ret+pred<=8:
        print(f"[{r}] خنجريّة {dg}→{do} | {out[:60]}")
print(f"\nمن {len(ayat)} آية (إدخالٌ مجرّد): استرجاع={ret} · تنبّؤ={pred} · فقدَ الخنجريّة={dagger_lost}")
# جرّب الإدخالَ الكاملَ (غير مجرّد) لنرى هل البحثُ يطابقُ حينها
print("\n=== نفسُ الآياتِ لكنْ بإدخالٍ كاملٍ (غير مجرّد) ===")
ret2=0
for g in ayat[:30]:
    out,route=diac_pipeline.diacritize(g, True)
    if "استرد" in route: ret2+=1
print(f"بإدخالٍ كامل: استرجاع={ret2}/{min(30,len(ayat))}")
