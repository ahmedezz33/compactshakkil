# -*- coding: utf-8 -*-
"""
jawf_diagnose2.py — تشخيص الحالات الحديّة من تحقّق الـ69:
هل غار/حاك/جار متجانسات فوّتها CAMeL؟ ولماذا كاد/خال/هان للمراجعة؟
يطبع لكل فعل: كل القراءات (root/gloss) + كل صيغ الماضي للمتكلّم + عين المضارع.
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.morphology.generator import Generator

VERBS = ["غار", "حاك", "جار", "طاف", "زال", "مار", "كاد", "خال", "هان"]
DIAC = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIAC)


def main():
    an = Analyzer(MorphologyDB.builtin_db(flags="a"))
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    for w in VERBS:
        print("\n" + "═" * 72)
        print(f"║ {w}")
        print("═" * 72)
        verbs = [a for a in an.analyze(w) if a.get("pos") == "verb"]
        seen = set()
        for a in verbs:
            k = (a.get("root"), a.get("gloss"))
            if k in seen: continue
            seen.add(k)
            print(f"   root={str(a.get('root','')):<9} gloss={str(a.get('gloss',''))[:44]}")
        try:
            past = gen.generate(w, {"pos": "verb", "asp": "p", "vox": "a", "per": "1", "num": "s"})
            print(f"   ماضي المتكلّم: {sorted({x.get('diac','') for x in past})}")
        except Exception as e:
            print(f"   خطأ توليد الماضي: {e}")
        try:
            pres = gen.generate(w, {"pos": "verb", "asp": "i"})
            mids = sorted({sd(x.get('diac',''))[2] for x in pres
                           if x.get('vox','a')=='a' and x.get('diac','').startswith('يَ')
                           and len(sd(x.get('diac','')))==4})
            print(f"   عين المضارع المعلوم: {mids}")
        except Exception as e:
            print(f"   خطأ توليد المضارع: {e}")


if __name__ == "__main__":
    _f = open("jawf_diagnose2_output.txt", "w", encoding="utf-8")
    class _T:
        def __init__(s, *x): s.x = x
        def write(s, y):
            for st in s.x:
                try: st.write(y)
                except Exception: pass
        def flush(s):
            for st in s.x:
                try: st.flush()
                except Exception: pass
    sys.stdout = _T(sys.stdout, _f); sys.stderr = sys.stdout
    try: main()
    finally: _f.flush(); _f.close()
