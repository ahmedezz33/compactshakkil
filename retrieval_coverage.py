# -*- coding: utf-8 -*-
"""
retrieval_coverage.py — قياس تغطية استرداد Reverence-Aware للقرآن (بلا نموذج).
يُثبت أنّ الآيات تُسترَدّ أصليّةً حرفيًّا (خطأ صفر = 100%).
"""
import sys
sys.path.insert(0, ".")
from pathlib import Path
from data.vocab_v2 import strip_diacritics

NORM_MAP = str.maketrans({"أ":"ا","إ":"ا","آ":"ا","ٱ":"ا","ى":"ي","ة":"ه"})
SMALL_ALIF = "ٰ"
# رموز قرآنيّة (فواصل/وقف) — تُزال للمطابقة فقط
QSYM = "".join(["۝","۞","ۖ","ۗ","ۘ","ۙ","ۚ","ۛ",
                "ۜ","۟","۠","ۡ","ۢ","ۣ","ۤ","ۥ",
                "ۦ","ۧ","ۨ","۩","۪","۫","۬","ۭ","۝"])
def _norm(s):
    s = strip_diacritics(s).replace(SMALL_ALIF,"")
    s = "".join(c for c in s if c not in QSYM)
    return " ".join(s.translate(NORM_MAP).split())

def build_index(path):
    idx={}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        orig=" ".join(line.split())
        if not orig: continue
        k=_norm(orig)
        if k and k not in idx: idx[k]=orig
    return idx

def main():
    idx=build_index("data/raw/quran/quran-simple.txt")
    keys=sorted(idx.keys(), key=len, reverse=True)
    print(f"الفهرس: {len(idx):,} آية")
    tests=[l for l in Path("data/raw/quran/quran-test.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    exact=embed=frag=miss=0
    char_err=char_tot=0
    for v in tests:
        v1=" ".join(v.split()); key=_norm(v1)
        out=None; route=None
        if key in idx: out=idx[key]; route="تامّة"; exact+=1
        else:
            for vk in keys:
                if len(vk)>=8 and vk in key: out=idx[vk]; route="مضمّنة"; embed+=1; break
            if out is None:
                for vk in reversed(keys):
                    if len(key)>=12 and key in vk: out=idx[vk]; route="مقطع"; frag+=1; break
        if out is None: miss+=1; continue
        # دقّة الاسترداد: هل النصّ المسترَدّ يطابق الآية الأصليّة حرفيًّا؟
        if route=="تامّة":
            a=list(strip_diacritics("".join(out.split())))
            # قارن على مستوى النصّ المشكّل الكامل بعد توحيد المسافات
            g=" ".join(v1.split()); o=" ".join(out.split())
            char_tot+=len(o)
            char_err+=sum(1 for x,y in zip(o,g) if x!=y)+abs(len(o)-len(g))
    n=len(tests)
    cov=exact+embed+frag
    print(f"\nآيات الاختبار: {n}")
    print(f"  تطابق تامّ (استرداد أصليّ 100%): {exact}  ({100*exact/n:.1f}%)")
    print(f"  مضمّنة: {embed}   مقطع: {frag}   غير مغطّاة (→ النموذج): {miss}")
    print(f"  تغطية الاسترداد الكلّيّة: {cov}/{n} = {100*cov/n:.1f}%")
    if char_tot:
        print(f"\n  دقّة النصّ المسترَدّ (تامّة) مقابل الأصل: DER={100*char_err/char_tot:.3f}%  "
              f"({'مطابقة حرفيّة تامّة' if char_err==0 else f'{char_err} فرق'})")

if __name__=="__main__":
    main()
