# -*- coding: utf-8 -*-
"""
make_clean_test.py — يبني مجموعة اختبارٍ خاليةً من التسرّب:
يُبقي فقط سطور test التي لا يظهر نصّها المجرّد (بلا تشكيل) في train.
المخرج: data/processed_clean/test_noleak.txt
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import strip_diacritics
TRAIN="data/processed_clean/train.txt"; TEST="data/processed_clean/test.txt"
OUT="data/processed_clean/test_noleak.txt"
def norm(s): return " ".join(strip_diacritics(s).split())
def main():
    tr=set()
    for line in open(TRAIN,encoding="utf-8"):
        s=line.strip()
        if s: tr.add(norm(s))
    print(f"train (مُطبّع): {len(tr):,}")
    kept=removed=0
    with open(TEST,encoding="utf-8") as f, open(OUT,"w",encoding="utf-8") as w:
        for line in f:
            s=line.strip()
            if not s: continue
            if norm(s) in tr: removed+=1
            else: w.write(s+"\n"); kept+=1
    print(f"أُبقي {kept:,}  |  أُزيل (مُسرَّب) {removed:,}  → {OUT}")
if __name__=="__main__": main()
