# -*- coding: utf-8 -*-
"""
check_overlap.py — تحقّقٌ رصين: هل تتسرّب جُمل الاختبار إلى التدريب؟
يقارن سطور test (مُطبّعةً: بلا تشكيل + مسافات موحّدة) بمجموعة سطور train.
تسرّبٌ عالٍ يُبطِل أرقام التقييم؛ تسرّبٌ صفر/ضئيل يؤكّد مصداقيّتها.
الاستخدام: python scripts/check_overlap.py
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import strip_diacritics

TRAIN="data/processed_clean/train.txt"
TEST ="data/processed_clean/test.txt"

def norm(s): return " ".join(strip_diacritics(s).split())

def main():
    test=set()
    for line in open(TEST,encoding="utf-8"):
        s=line.strip()
        if s: test.add(norm(s))
    print(f"سطور الاختبار الفريدة (مُطبّعة): {len(test):,}")
    seen=0; hit=0; hits=[]
    tr=set()
    for line in open(TRAIN,encoding="utf-8"):
        s=line.strip()
        if not s: continue
        seen+=1
        n=norm(s)
        if n in test:
            hit+=1
            if len(hits)<10: hits.append(n)
    print(f"سطور التدريب: {seen:,}")
    print(f"تطابقاتٌ حرفيّة (تسرّب): {hit:,}")
    # نسبة سطور الاختبار المُسرَّبة
    tset=set()
    for line in open(TRAIN,encoding="utf-8"):
        s=line.strip()
        if s: tset.add(norm(s))
    leaked=sum(1 for t in test if t in tset)
    print(f"سطور اختبارٍ ظهرت في التدريب: {leaked:,} = {100*leaked/max(1,len(test)):.2f}% من الاختبار")
    print("="*56)
    if leaked==0: print("✅ لا تسرّب — أرقام التقييم موثوقة تمامًا")
    elif 100*leaked/len(test) < 1: print("✅ تسرّبٌ ضئيلٌ جدًّا (<1%) — لا يؤثّر عمليًّا")
    else: print("⚠️ تسرّبٌ ملموس — يجب إعادة التقسيم وإعادة القياس")
    if hits:
        print("\nأمثلة على المتطابق:")
        for h in hits[:5]: print("  "+h[:70])

if __name__=="__main__":
    main()
