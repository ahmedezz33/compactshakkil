# -*- coding: utf-8 -*-
"""
resolve_hollow_v5.py — الخوارزمية الذهبيّة (مبنيّة على البيانات الكاملة)

المبدأ المثبَت بمخرجات CAMeL الفعلية:
  • حقل root يضع # مكان المعتلّ (حتى في الأسماء) → عديم الفائدة للأصل.
  • تحليل الماضي المجرّد (pattern/diac/lex/bw) كلّه ألف سطحيّة.
  • توليد المضارع بخصائص مفصّلة يرجع فارغًا (خلل خصائص) → لا يُعتمد عليه.
  • ✅ الإشارة العاملة والأدقّ = حركة الحرف الأوّل في الماضي للمتكلّم:
        ضمّة (قُلْتُ) → واو [يقين]
        كسرة (بِعْتُ) → ياء [يصحّ إلا في فَعِلَ يَفْعَلُ الواويّ: خِفْتُ/نِمْتُ]

المراحل (فلسفة: المؤكّد يُعتمد، المشكوك يُراجع):
  1) ضمّة → واو (ثقة عالية، نهائيّ).
  2) كسرة + ليست في القائمة المغلقة → ياء (ثقة عالية).
  3) كسرة + في القائمة المغلقة المُحقَّقة (خاف/نام...) → واو (لَكسِن/مصدر).
  4) تعذّر التوليد أو حركة غير متوقّعة → مراجعة يدوية.
"""
import sys, io
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
try:
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.morphology.generator import Generator
except Exception as e:
    print("خطأ استيراد CAMeL:", e); sys.exit(1)

WAW, YA = "و", "ي"
DAMMA, KASRA, FATHA = "ُ", "ِ", "َ"

# المرحلة 3: قائمة مغلقة مُحقَّقة فقط لأفعال فَعِلَ يَفْعَلُ الواويّة
#            (ماضيها كسرة لكن أصلها واو — يُحسم بالمصدر، لا بالتصريف).
#            تنمو بالتحقّق البصريّ/المصدر فقط — لا تخمين.
KASRA_BUT_WAW = {
    "خاف": WAW,   # المصدر: خَوْف
    "نام": WAW,   # المصدر: نَوْم
}

TEST = [
    ("قال", WAW), ("باع", YA), ("صام", WAW), ("طال", WAW), ("دار", WAW),
    ("كان", WAW), ("زاد", YA), ("خاف", WAW), ("نام", WAW), ("مات", WAW),
    ("طاب", YA), ("هاب", YA), ("سار", YA),
]

def past_1s_vowel(generator, lemma):
    """يُرجع (الحركة على الحرف الأوّل, صيغة الماضي للمتكلّم)."""
    try:
        gens = generator.generate(lemma, {"pos": "verb", "asp": "p",
                                          "vox": "a", "per": "1", "num": "s"})
    except Exception as e:
        return None, f"<err:{e}>"
    for g in gens:
        form = g.get("diac", "")
        # الحرف الأوّل ثمّ حركته مباشرة
        if len(form) >= 2 and form[1] in (DAMMA, KASRA, FATHA):
            return form[1], form
    return None, (gens[0].get("diac", "") if gens else None)

def resolve(generator, lemma):
    vowel, form = past_1s_vowel(generator, lemma)
    if vowel == DAMMA:
        return {"letter": WAW, "conf": "confirmed", "stage": "past1s_damma→waw", "form": form}
    if vowel == KASRA:
        if lemma in KASRA_BUT_WAW:
            return {"letter": KASRA_BUT_WAW[lemma], "conf": "confirmed",
                    "stage": "closed_list_faIl_waw", "form": form}
        return {"letter": YA, "conf": "confirmed", "stage": "past1s_kasra→ya", "form": form}
    return {"letter": None, "conf": "review", "stage": "needs_review", "form": form}

def main():
    print("=" * 74)
    print("resolve_hollow_v5 — الحلّ عبر ماضي المتكلّم + قائمة مغلقة")
    print("=" * 74)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))

    confirmed, review, correct = [], [], 0
    print(f"\n{'الفعل':<7}{'الماضي':<10}{'الأصل':<7}{'الناتج':<7}{'المرحلة':<24}{'الحكم'}")
    print("-" * 74)
    for lemma, truth in TEST:
        r = resolve(gen, lemma)
        letter = r["letter"] or "؟"
        ok = "✅" if r["letter"] == truth else ("🔍" if r["conf"] == "review" else "❌")
        if r["letter"] == truth:
            correct += 1
        (confirmed if r["conf"] == "confirmed" else review).append((lemma, r))
        print(f"{lemma:<7}{str(r['form']):<10}{truth:<7}{letter:<7}{r['stage']:<24}{ok}")

    n = len(TEST)
    print("-" * 74)
    print(f"مؤكَّد: {len(confirmed)}   |   مراجعة: {len(review)}   |   الدقّة: {correct}/{n} = {100*correct//n}%")
    print("\n[ملفّ المؤكَّد — يُعتمد آليًا]")
    for lemma, r in confirmed:
        print(f"   {lemma} → {r['letter']}   ({r['stage']})")
    print("\n[ملفّ المراجعة — يُعرَض على الإنسان]")
    print("   " + ("، ".join(l for l, _ in review) if review else "(فارغ)"))

if __name__ == "__main__":
    _f = open("jawf_v5_output.txt", "w", encoding="utf-8")
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
