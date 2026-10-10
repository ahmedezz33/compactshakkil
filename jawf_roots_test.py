# -*- coding: utf-8 -*-
"""
jawf_roots_test.py — اختبار استخراج CAMeL للجذر من الأسرة الاشتقاقية الكاملة.

لجذور متقاربة (زاغ، كاد/كيد، حرّ/حار)، نُجري تحليل CAMeL على كل مشتقّ
(مصدر/صفة/جمع/أوزان/مضارع) ونطبع: الجذر + الوزن + النوع + المعنى.
الهدف: قياس هل يلمّ CAMeL الأسرة لجذر واحد، وأين يخفق (#، جذر خاطئ، تشتّت).
"""
import sys
from collections import Counter
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

DIAC = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIAC)

SETS = {
    "المجموعة 1 — ز.و.غ / ز.ي.غ (زاغ)": [
        "زيغان", "زاغ", "زوغ", "مزوغ", "زوغان", "ازاغ", "يزوغ", "يزيغ",
    ],
    "المجموعة 2 — ك.ي.د (كاد/كيد)": [
        "كيود", "مكيدون", "مكايد", "مكائد", "كياد", "مكيدة", "كيد", "مكيد",
        "كاد", "كايد", "اكتاد", "تكايد", "يكيد", "يكايد", "يكتاد", "يتكايد",
    ],
    "المجموعة 3 — ح.ر.ر / ح.و.ر (حرّ/حار)": [
        "محر", "حار", "محرور", "حريري", "حراريات", "حرور", "محار", "احرار",
        "حرار", "حرائر", "حر", "احر", "حرية", "حرورية", "حرى", "حرير",
        "حران", "حرار", "حرة", "استحر", "احر", "حرر", "يحر", "يحر", "يستحر",
        "يحرر",
    ],
}


def analyze_form(an, form):
    """يُرجع قائمة (root, pos, pattern, gloss) مميّزة."""
    out, seen = [], set()
    for a in an.analyze(sd(form)):
        key = (a.get("root"), a.get("pos"), a.get("gloss"))
        if key in seen:
            continue
        seen.add(key)
        out.append((a.get("root", ""), a.get("pos", ""),
                    a.get("pattern", ""), str(a.get("gloss", ""))[:34]))
    return out


def main():
    an = Analyzer(MorphologyDB.builtin_db(flags="a"))
    for title, forms in SETS.items():
        print("\n" + "═" * 74)
        print(f"║ {title}")
        print("═" * 74)
        root_counter = Counter()
        for form in forms:
            analyses = analyze_form(an, form)
            print(f"\n▌ {form}  ({len(analyses)} تحليل)")
            for root, pos, pat, gloss in analyses[:5]:
                print(f"    root={root:<9} pos={pos:<6} pat={pat:<8} {gloss}")
                root_counter[root] += 1
        print(f"\n  ── توزيع الجذور في المجموعة ──")
        for root, cnt in root_counter.most_common(8):
            print(f"     {root:<10} × {cnt}")


if __name__ == "__main__":
    _f = open("jawf_roots_output.txt", "w", encoding="utf-8")
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
