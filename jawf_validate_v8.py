# -*- coding: utf-8 -*-
"""
jawf_validate_v8.py — تحقّق موسّع لخوارزمية v8 على ~75 فعلاً أجوف.

يستورد منطق v8 نفسه من resolve_hollow_v8، ويقيس:
  • التوزيع: قاعدة صرفية / معجم صنف الألف / متجانس / مراجعة.
  • الدقّة على مجموعة ذهبية مُقترَحة (تحتاج تأكيد أحمد).
  • حِمل المراجعة، وقائمة المتجانسات المكتشَفة، وأيّ تعارض بين v8 وتسميتي.

⚠️ التسميات الذهبية من الصرف، مقترحة للتحقّق البشريّ (human-in-the-loop).
التشغيل:  .\\venv\\Scripts\\python.exe jawf_validate_v8.py
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.generator import Generator
from resolve_hollow_v8 import resolve, WAW, YA   # منطق v8 نفسه

# ~75 فعلاً أجوف. التسمية: و / ي / ألف(صنف فَعِلَ) / متجانس(جذران) / None(بلا تسمية)
VERBS = [
    # واويّ (فَعَلَ يَفْعُلُ) — ماضٍ ضمّة
    ("قال", WAW), ("قام", WAW), ("صام", WAW), ("دام", WAW), ("عاد", WAW),
    ("زار", WAW), ("فاز", WAW), ("دار", WAW), ("كان", WAW), ("مات", WAW),
    ("تاب", WAW), ("ذاق", WAW), ("طاف", WAW), ("قاد", WAW), ("ثار", WAW),
    ("لام", WAW), ("خان", WAW), ("صان", WAW), ("عام", WAW), ("ناح", WAW),
    ("جاد", WAW), ("ساد", WAW), ("فار", WAW), ("راح", WAW), ("ساق", WAW),
    ("فاق", WAW), ("ذاب", WAW), ("طال", WAW), ("ذاد", WAW), ("عاق", WAW),
    # يائيّ (فَعَلَ يَفْعِلُ) — ماضٍ كسرة + مضارع ياء
    ("باع", YA), ("زاد", YA), ("طاب", YA), ("سار", YA), ("صار", YA),
    ("طار", YA), ("غاب", YA), ("عاش", YA), ("سال", YA), ("دان", YA),
    ("حان", YA), ("زان", YA), ("هام", YA), ("فاض", YA), ("ذاع", YA),
    ("صاح", YA), ("ضاق", YA), ("شاع", YA), ("عاب", YA), ("كال", YA),
    ("مال", YA), ("باد", YA),
    # صنف الألف (فَعِلَ يَفْعَلُ) — في المعجم
    ("خاف", WAW), ("نام", WAW), ("هاب", YA), ("شاء", YA),
    # صنف الألف — خارج المعجم (متوقّع: مراجعة)
    ("كاد", None), ("خال", None), ("زال", None),
    # متجانسات محتملة (متوقّع: كشف بجذرين)
    ("ضاع", None), ("شاب", None), ("نال", None), ("زاغ", None), ("حار", None),
    ("غار", None), ("جار", None), ("مار", None), ("حاك", None),
    # ثغرة معروفة
    ("هان", None),
]


def main():
    print("=" * 84)
    print(f"jawf_validate_v8 — تحقّق موسّع على {len(VERBS)} فعلاً")
    print("=" * 84)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))

    dist = {"rule": 0, "lexicon": 0, "homograph": 0, "review": 0}
    gold_total = gold_ok = 0
    homographs, reviews, conflicts = [], [], []

    print(f"\n{'الفعل':<7}{'المتوقّع':<9}{'الناتج':<7}{'المرحلة':<24}{'حكم'}")
    print("-" * 84)
    for lemma, gold in VERBS:
        r = resolve(gen, lemma)
        conf, stage, letter = r["conf"], r["stage"], r["letter"]
        # تصنيف التوزيع
        if conf == "homograph":
            dist["homograph"] += 1; homographs.append(lemma)
        elif conf == "review":
            dist["review"] += 1; reviews.append(lemma)
        elif "معجم" in stage:
            dist["lexicon"] += 1
        else:
            dist["rule"] += 1

        mark = "—"
        if gold in (WAW, YA):
            gold_total += 1
            if letter == gold:
                gold_ok += 1; mark = "✅"
            elif conf in ("homograph", "review"):
                mark = "🔍"  # لم يُحسم (مقبول)
            else:
                mark = "❌"; conflicts.append((lemma, gold, letter))
        elif conf == "homograph":
            mark = "🔀"
        elif conf == "review":
            mark = "🔍"
        print(f"{lemma:<7}{str(gold or '—'):<9}{str(letter or '؟'):<7}{stage:<24}{mark}")

    n = len(VERBS)
    print("-" * 84)
    print(f"التوزيع: قاعدة={dist['rule']}  معجم={dist['lexicon']}  متجانس={dist['homograph']}  مراجعة={dist['review']}  (من {n})")
    if gold_total:
        print(f"الدقّة على المُسمّى المحسوم: {gold_ok}/{gold_total} = {100*gold_ok//gold_total}%")
    print(f"متجانسات مكتشَفة ({len(homographs)}): {'، '.join(homographs)}")
    print(f"للمراجعة ({len(reviews)}): {'، '.join(reviews)}")
    print(f"\n⚠️ تعارض v8 مع تسميتي (يحتاج فحصك): {conflicts or 'لا يوجد ✅'}")


if __name__ == "__main__":
    _f = open("jawf_validate_v8_output.txt", "w", encoding="utf-8")
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
