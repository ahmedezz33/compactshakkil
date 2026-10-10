# -*- coding: utf-8 -*-
"""
explore_all.py — استكشاف كامل بلا فلترة (كل القراءات: اسم/فعل/مجهول)
الهدف: كشف أيّ إشارة مغفَلة تميّز الأصل الواويّ/اليائيّ قبل بناء الخوارزمية.

لكل كلمة يطبع:
  • كل التحليلات (كل pos) مع: pos, root, lex, diac, vox, pattern, stemcat, gloss
  • توليد المضارع المعلوم (3ms) + المبنيّ للمجهول
  • توليد الماضي للمتكلّم (1s) — لكشف حركة قُلت/بِعت/خِفت
"""
import sys, io
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

DIACS = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIACS)

WORDS = [
    ("قال","و"),("باع","ي"),("صام","و"),("طال","و"),("دار","و"),
    ("كان","و"),("زاد","ي"),("خاف","و"),("نام","و"),("مات","و"),
    ("طاب","ي"),("هاب","ي"),("سار","ي"),
]

def gen_forms(generator, lemma, feats):
    try:
        return [g.get("diac","") for g in generator.generate(lemma, feats)]
    except Exception as e:
        return [f"<err:{e}>"]

def main():
    dba = MorphologyDB.builtin_db(flags="a")
    dbg = MorphologyDB.builtin_db(flags="g")
    an = Analyzer(dba); gen = Generator(dbg)

    for word, truth in WORDS:
        print("\n" + "═"*76)
        print(f"║ {word}   (الأصل الصحيح: {truth})")
        print("═"*76)
        analyses = an.analyze(word)
        print(f"إجمالي التحليلات (كل القراءات): {len(analyses)}")
        # جدول مضغوط لكل تحليل
        print(f"  {'pos':<8}{'root':<10}{'lex':<8}{'diac':<9}{'vox':<5}{'pattern':<9}{'stemcat':<14}gloss")
        seen = set()
        for a in analyses:
            key = (a.get('pos'), a.get('root'), a.get('lex'), a.get('vox'), a.get('pattern'))
            if key in seen:
                continue
            seen.add(key)
            print(f"  {str(a.get('pos','')):<8}{str(a.get('root','')):<10}"
                  f"{str(a.get('lex','')):<8}{str(a.get('diac','')):<9}"
                  f"{str(a.get('vox','')):<5}{str(a.get('pattern','')):<9}"
                  f"{str(a.get('stemcat','')):<14}{str(a.get('gloss',''))[:34]}")
        # التوليد الموجَّه
        pres_a = gen_forms(gen, word, {"pos":"verb","asp":"i","mod":"i","vox":"a","per":"3","gen":"m","num":"s"})
        pres_p = gen_forms(gen, word, {"pos":"verb","asp":"i","mod":"i","vox":"p","per":"3","gen":"m","num":"s"})
        past_1s = gen_forms(gen, word, {"pos":"verb","asp":"p","vox":"a","per":"1","num":"s"})
        print(f"\n  المضارع المعلوم (3ms):  {pres_a}")
        print(f"  المضارع المجهول (3ms): {pres_p}")
        print(f"  الماضي المتكلّم (1s):   {past_1s}")

if __name__ == "__main__":
    _f = open("explore_output.txt","w",encoding="utf-8")
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
