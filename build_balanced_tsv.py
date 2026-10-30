# -*- coding: utf-8 -*-
"""build_balanced_tsv.py — مانيفستٌ موحَّدٌ *متوازن* يمنعُ طغيانَ التراثِ على القرآن.
القرآنُ يُكرَّرُ ×QREP (أخذُ عيّناتٍ زائد)، والتراثُ يُحَدُّ اختياريًّا بسقف CCAP.
بيئة: QREP (افتراضي 2) · CCAP (0=بلا سقف) · OUT (افتراضي data/ocr_unified_balanced.tsv).
يطبعُ التركيبَ والنسبةَ الناتجة. يعملُ على الجسرِ بلا GPU."""
import os, random, re
random.seed(20)
_WAQF=re.compile(r"[\u06D6-\u06ED]")
QREP=int(os.environ.get("QREP","2")); CCAP=int(os.environ.get("CCAP","0"))
OUT=os.environ.get("OUT","data/ocr_unified_balanced.tsv")
def read(d):
    mf=os.path.join(d,"manifest.tsv"); out=[]
    if not os.path.exists(mf): print("⚠️ مفقود:",mf); return out
    for ln in open(mf,encoding="utf-8"):
        ln=ln.rstrip("\n")
        if "\t" not in ln: continue
        rel,txt=ln.split("\t",1); rel=rel.lstrip("/").replace("\\","/")
        g=_WAQF.sub("",txt).strip()
        if g: out.append(f"{d}/{rel}\t{g}")
    return out
quran=read("data/ocr_quran_pages")
classical=read("data/ocr_classical_pages")+read("data/ocr_classical_pages_more")
random.shuffle(classical)
if CCAP>0: classical=classical[:CCAP]
qall=[]
for _ in range(max(1,QREP)): qall+=quran
rows=qall+classical; random.shuffle(rows)
open(OUT,"w",encoding="utf-8").write("\n".join(rows)+"\n")
c=len(classical); q=len(qall); qu=len(quran)
print(f"قرآن أساس={qu} ×{QREP} = {q} سطرًا")
print(f"تراث={c} سطرًا" + (f" (سقف {CCAP})" if CCAP>0 else " (بلا سقف)"))
print(f"المجموع={len(rows)} → {OUT}")
print(f"نسبة تراث:قرآن = {c/max(1,q):.2f} : 1")
