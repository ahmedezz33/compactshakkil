# -*- coding: utf-8 -*-
"""
clean_data.py — تنظيف بيانات التشكيل (الخطوة ١): إبقاء السطور المكتملة فقط.

التشوّه المهيمن: نصوص جزئيّة التشكيل (min_diac_ratio=0.4 القديم أدخل ناقصات).
هنا نُبقي فقط السطور التي تُشكَّل فيها ≥ العتبة من الصوامت الصريحة → مرجع موثوق.

يطبع أوّلًا جدول إبقاء عند عتبات عدّة (لاختيار العتبة)، ثمّ يكتب عند العتبة المختارة.

الاستخدام:
    python clean_data.py <in_dir> <out_dir> [threshold] [dagger:keep|strip|exclude]
مثال:
    python clean_data.py data/processed data/processed_clean 0.98 keep
"""
import sys, os
from pathlib import Path
sys.path.insert(0, ".")
from data.vocab import split_letters_and_diacritics, ARABIC_LETTERS

SPACE=" "; DAGGER="ٰ"
NON_CONS=set("اآىويءؤئأإ"); CONS=set(ARABIC_LETTERS)-NON_CONS
SPLITS=["train","val","test"]

def completeness(letters, classes):
    cons=cbare=0
    for i,ch in enumerate(letters):
        if ch in CONS:
            cons+=1
            if classes[i]==0: cbare+=1
    return (cons-cbare)/cons if cons else 1.0, cons

def scan(path):
    """يمسح ملفًّا ويُرجع قائمة (raw, ratio, has_dagger, n_letters)."""
    rows=[]
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            raw=line.strip()
            if not raw: continue
            letters,classes=split_letters_and_diacritics(raw)
            if len(letters)<3 or len(letters)>300: continue
            r,cons=completeness(letters,classes)
            if cons==0: continue
            rows.append((raw, r, DAGGER in raw))
    return rows

def main():
    in_dir, out_dir = sys.argv[1], sys.argv[2]
    thr = float(sys.argv[3]) if len(sys.argv)>3 else 0.98
    dagger = sys.argv[4] if len(sys.argv)>4 else "keep"
    os.makedirs(out_dir, exist_ok=True)
    print("="*68); print("تنظيف بيانات التشكيل — الخطوة ١"); print("="*68)
    print(f"العتبة={thr}  سياسة الألف الخنجريّة={dagger}")

    for split in SPLITS:
        p = Path(in_dir)/f"{split}.txt"
        if not p.exists():
            print(f"\n[{split}] غير موجود — تجاوز"); continue
        rows = scan(str(p))
        n=len(rows)
        print(f"\n[{split}] سطور صالحة={n:,}")
        # جدول إبقاء
        for t in [0.95,0.98,0.99,1.0]:
            k=sum(1 for _,r,_ in rows if r>=t)
            print(f"   ≥{t:.2f}: يُبقى {k:,} ({100.0*k/max(1,n):.1f}%)")
        withd=sum(1 for _,_,d in rows if d)
        print(f"   تحوي ألفًا خنجريّة: {withd:,} ({100.0*withd/max(1,n):.1f}%)")
        # الكتابة عند العتبة المختارة
        outp = Path(out_dir)/f"{split}.txt"
        kept=0
        with open(outp,"w",encoding="utf-8") as w:
            for raw,r,d in rows:
                if r < thr: continue
                if d and dagger=="exclude": continue
                if d and dagger=="strip": raw = raw.replace(DAGGER,"")
                w.write(raw+"\n"); kept+=1
        print(f"   ✅ كُتب {kept:,} سطر → {outp}")

if __name__=="__main__":
    main()
