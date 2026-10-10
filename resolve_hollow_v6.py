# -*- coding: utf-8 -*-
"""
resolve_hollow_v6.py — الخوارزمية الذهبيّة (إشارتان: الماضي + المضارع)

الأساس الصرفيّ (مؤكَّد):
  وزن فَعِلَ يَفْعَلُ الأجوف يقلب العين (و/ي) ألفًا بالإعلال:
    خاف ← خَوِفَ يَخْوَفُ (عين واو)  |  شاء ← شَيِئَ يَشيَأُ (عين ياء)
  فالواويّ واليائيّ في هذا الصنف كلاهما: ماضيه كسرة + مضارعه ألف
  → لا يفصلهما التصريف؛ الفاصل هو المصدر (خَوْف / شيء) → معجم/مراجعة.

منطق القرار (إشارتان مستقلّتان):
  الماضي 1س ضمّة (قُلْتُ)                → واو [يقين: فَعَلَ يَفْعُل]
  الماضي 1س كسرة + المضارع عينه ياء     → ياء [يقين: فَعَلَ يَفْعِل]
  الماضي 1س كسرة + المضارع عينه واو     → واو [نادر]
  الماضي 1س كسرة + المضارع عينه ألف     → فَعِلَ يَفْعَلُ الأجوف:
        • في المعجم المُحقَّق → يُعتمد
        • غير ذلك            → مراجعة يدوية (لا يُخمَّن أبدًا)
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

WAW, YA, ALIF = "و", "ي", "ا"
DAMMA, KASRA = "ُ", "ِ"
DIACS = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIACS)

# معجم مُحقَّق لصنف الألف (فَعِلَ يَفْعَلُ الأجوف) — يُحسم بالمصدر لا بالتصريف.
# يُزاد إليه بالتحقّق فقط (لا تخمين).
ALIF_HOLLOW_LEX = {
    "خاف": WAW,   # خَوْف
    "نام": WAW,   # نَوْم
    "شاء": YA,    # مشيئة / شيء
    "هاب": YA,    # هَيْبة
}

TEST = [
    ("قال", WAW), ("باع", YA), ("صام", WAW), ("طال", WAW), ("دار", WAW),
    ("كان", WAW), ("زاد", YA), ("خاف", WAW), ("نام", WAW), ("مات", WAW),
    ("طاب", YA), ("هاب", YA), ("سار", YA), ("شاء", YA),
]

def past1s_vowel(gen, lemma):
    try:
        g = gen.generate(lemma, {"pos": "verb", "asp": "p", "vox": "a",
                                 "per": "1", "num": "s"})
    except Exception:
        return None, None
    for a in g:
        f = a.get("diac", "")
        if len(f) >= 2 and f[1] in (DAMMA, KASRA):
            return f[1], f
    return None, (g[0].get("diac", "") if g else None)

def present_middle(gen, lemma):
    """عين المضارع من صيغة المعلوم 3م المفرد (يَ.. بطول 4 حروف)."""
    try:
        g = gen.generate(lemma, {"pos": "verb", "asp": "i"})   # خصائص فضفاضة (تعمل)
    except Exception:
        return None, None
    for a in g:
        if a.get("vox", "a") != "a":
            continue
        diac = a.get("diac", "")
        if not diac.startswith("يَ"):      # المعلوم يبدأ بـ يَ (المجهول يُ)
            continue
        bare = sd(diac)
        if bare.startswith("ي") and len(bare) == 4:
            return bare[2], diac
    return None, None

def resolve(gen, lemma):
    pv, pform = past1s_vowel(gen, lemma)
    mid, mform = present_middle(gen, lemma)
    sig = f"ماضٍ={pform or '—'} | مضارع عينه={mid or '—'}"

    if pv == DAMMA:
        return {"letter": WAW, "conf": "confirmed", "stage": "ضمّة→واو", "sig": sig}
    if pv == KASRA:
        if mid == YA:
            return {"letter": YA, "conf": "confirmed", "stage": "كسرة+ياء→ياء", "sig": sig}
        if mid == WAW:
            return {"letter": WAW, "conf": "confirmed", "stage": "كسرة+واو→واو", "sig": sig}
        if mid == ALIF:   # فَعِلَ يَفْعَلُ الأجوف
            if lemma in ALIF_HOLLOW_LEX:
                return {"letter": ALIF_HOLLOW_LEX[lemma], "conf": "confirmed",
                        "stage": "صنف الألف: معجم", "sig": sig}
            return {"letter": None, "conf": "review", "stage": "صنف الألف: مراجعة", "sig": sig}
    return {"letter": None, "conf": "review", "stage": "تعذّر التوليد → مراجعة", "sig": sig}

def main():
    print("=" * 80)
    print("resolve_hollow_v6 — إشارتان (الماضي + المضارع) + معجم صنف الألف")
    print("=" * 80)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    confirmed, review, correct = [], [], 0
    print(f"\n{'الفعل':<7}{'الأصل':<7}{'الناتج':<7}{'المرحلة':<22}{'الإشارة'}")
    print("-" * 80)
    for lemma, truth in TEST:
        r = resolve(gen, lemma)
        letter = r["letter"] or "؟"
        ok = "✅" if r["letter"] == truth else ("🔍" if r["conf"] == "review" else "❌")
        if r["letter"] == truth: correct += 1
        (confirmed if r["conf"] == "confirmed" else review).append((lemma, truth, r))
        print(f"{lemma:<7}{truth:<7}{letter:<7}{r['stage']:<22}{r['sig']}  {ok}")
    n = len(TEST)
    print("-" * 80)
    print(f"مؤكَّد: {len(confirmed)}   |   مراجعة: {len(review)}   |   دقّة المؤكَّد+المعجم: {correct}/{n} = {100*correct//n}%")
    print("\n[للمراجعة اليدوية]:", "، ".join(f"{l}" for l, _, _ in review) or "(فارغ)")
    # فحص أمانة: هل أيّ مؤكَّد خاطئ؟
    wrong = [(l, t, r['letter']) for l, t, r in confirmed if r['letter'] != t]
    print("[أخطاء في المؤكَّد]:", wrong or "لا يوجد ✅")

if __name__ == "__main__":
    _f = open("jawf_v6_output.txt", "w", encoding="utf-8")
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
