# -*- coding: utf-8 -*-
"""
jawf_diagnose.py — تشخيص الأفعال الشاذّة الستّة:
هل الخطأ تصادم متجانسات (جذور متعدّدة) أم خلل حقيقيّ؟
يطبع لكل فعل: كل قراءات analyze (root/lex/diac/gloss) + كل صيغ ماضي المتكلّم.
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
try:
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.morphology.analyzer import Analyzer
    from camel_tools.morphology.generator import Generator
except Exception as e:
    print("خطأ استيراد CAMeL:", e); sys.exit(1)

ANOMALIES = ["ضاع", "شاب", "نال", "زاغ", "حار", "هان"]

def main():
    an = Analyzer(MorphologyDB.builtin_db(flags="a"))
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    for w in ANOMALIES:
        print("\n" + "═"*72)
        print(f"║ {w}")
        print("═"*72)
        analyses = an.analyze(w)
        verbs = [a for a in analyses if a.get("pos") == "verb"]
        print(f"تحليلات الفعل: {len(verbs)} (من {len(analyses)} إجمالاً)")
        seen = set()
        for a in verbs:
            k = (a.get("root"), a.get("lex"), a.get("gloss"))
            if k in seen: continue
            seen.add(k)
            print(f"   root={a.get('root',''):<9} lex={a.get('lex',''):<7} "
                  f"diac={a.get('diac',''):<8} gloss={str(a.get('gloss',''))[:40]}")
        # كل صيغ ماضي المتكلّم المولّدة (لرؤية الضمّة/الكسرة الفعلية)
        try:
            g = gen.generate(w, {"pos":"verb","asp":"p","vox":"a","per":"1","num":"s"})
            print(f"   ماضي المتكلّم المولّد: {sorted({x.get('diac','') for x in g})}")
        except Exception as e:
            print(f"   خطأ توليد الماضي: {e}")

if __name__ == "__main__":
    _f = open("jawf_diagnose_output.txt","w",encoding="utf-8")
    class _T:
        def __init__(s,*x): s.x=x
        def write(s,y):
            for st in s.x:
                try: st.write(y)
                except Exception: pass
        def flush(s):
            for st in s.x:
                try: st.flush()
                except Exception: pass
    sys.stdout=_T(sys.stdout,_f); sys.stderr=sys.stdout
    try: main()
    finally: _f.flush(); _f.close()
