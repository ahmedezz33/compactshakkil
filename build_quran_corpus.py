# -*- coding: utf-8 -*-
"""build_quran_corpus.py — مدوّنةُ قرآنٍ نظيفةٌ من metadata (تشكيلٌ موثوق، نطاقٌ متميّز)."""
import re, csv, sys
# رموزُ المصحفِ غيرُ القياسيّة (ماعدا الحركاتِ والخنجريّة): تُحذَف
_QSYM = re.compile(r"[ۖ-ۜ۝۞۟۠-ۤۧ-۩۪-ࣰۭ-ࣿ]")
_H = "ًٌٍَُِّْٰ"; _STRIP = str.maketrans("", "", _H)
def bare(s): return s.translate(_STRIP)
def load_test_keys(p="data/processed_clean/test_clean.txt"):
    k=set()
    try:
        for l in open(p,encoding="utf-8"):
            b=bare(l.strip())
            if b: k.add(b)
    except FileNotFoundError: pass
    return k
def main():
    keys=load_test_keys(); seen=set(); out=[]
    with open("train_data/minshawy/metadata.csv",encoding="utf-8") as f:
        next(f,None)
        for line in f:
            if "|" not in line: continue
            t=line.split("|",1)[1].strip()
            t=_QSYM.sub("",t); t=re.sub(r"[ \t]{2,}"," ",t).strip()
            if len(t.split())<2: continue
            b=bare(t)
            if not b or b in seen or b in keys: continue
            seen.add(b); out.append(t)
    import os; os.makedirs("data/processed_quran",exist_ok=True)
    open("data/processed_quran/quran_clean.txt","w",encoding="utf-8").write("\n".join(out)+"\n")
    print(f"✅ قرآنٌ نظيف: {len(out):,} آية → data/processed_quran/quran_clean.txt")
if __name__=="__main__": main()
