# -*- coding: utf-8 -*-
"""
resolve_hollow_v7.py — الخوارزمية الذهبيّة (إصلاح استخراج عين المضارع)

إصلاح v6→v7:
  كان استخراج عين المضارع يلتقط صيغًا بلواحق (يَقُلْنَ → الحرف الثالث)،
  فيخرج حرفًا صحيحًا لا معتلًّا. الإصلاح: نختار صيغة المضارع التي
  عينها (الحرف الأوسط) معتلّة (و/ي/ا) حصرًا — وهي صيغة الأجوف الأساسية.

منطق القرار (إشارتان):
  ماضٍ 1س ضمّة (قُلْتُ)                  → واو [يقين: فَعَلَ يَفْعُل]
  ماضٍ 1س كسرة + عين المضارع ياء (يَبِيع) → ياء [يقين: فَعَلَ يَفْعِل]
  ماضٍ 1س كسرة + عين المضارع واو         → واو [نادر]
  ماضٍ 1س كسرة + عين المضارع ألف (يَخاف)  → فَعِلَ يَفْعَلُ الأجوف الغامض:
        • في المعجم المُحقَّق → يُعتمد
        • غير ذلك            → مراجعة (لا يُخمَّن مجهول أبدًا)
  تعذّر تحديد الماضي                     → مراجعة
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
WEAK = (WAW, YA, ALIF)
DAMMA, KASRA = "ُ", "ِ"
DIACS = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIACS)

# معجم مُحقَّق لصنف الألف (فَعِلَ يَفْعَلُ الأجوف) — يُحسم بالمصدر لا بالتصريف.
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
    """عين المضارع = الحرف الأوسط المعتلّ في صيغة المعلوم (يَ..) بطول 4 حروف مجرّدة."""
    try:
        g = gen.generate(lemma, {"pos": "verb", "asp": "i"})
    except Exception:
        return None, None
    for a in g:
        if a.get("vox", "a") != "a":
            continue
        diac = a.get("diac", "")
        if not diac.startswith("يَ"):
            continue
        bare = sd(diac)
        # صيغة الأجوف الأساسية: يَ + فاء + (عين معتلّة) + لام
        if len(bare) == 4 and bare[2] in WEAK:
            return bare[2], diac
    return None, None

def resolve(gen, lemma):
    pv, pform = past1s_vowel(gen, lemma)
    mid, mform = present_middle(gen, lemma)
    sig = f"ماضٍ={pform or '—'} | عين المضارع={mid or '—'}"

    if pv == DAMMA:
        return {"letter": WAW, "conf": "confirmed", "stage": "ضمّة→واو", "sig": sig}
    if pv == KASRA:
        if mid == YA:
            return {"letter": YA, "conf": "confirmed", "stage": "كسرة+ياء→ياء", "sig": sig}
        if mid == WAW:
            return {"letter": WAW, "conf": "confirmed", "stage": "كسرة+واو→واو", "sig": sig}
        # عين ألف أو تعذّر تحديدها → صنف فَعِلَ الغامض
        if lemma in ALIF_HOLLOW_LEX:
            return {"letter": ALIF_HOLLOW_LEX[lemma], "conf": "confirmed",
                    "stage": "صنف الألف: معجم", "sig": sig}
        return {"letter": None, "conf": "review", "stage": "صنف الألف: مراجعة", "sig": sig}
    return {"letter": None, "conf": "review", "stage": "تعذّر الماضي → مراجعة", "sig": sig}

def main():
    print("=" * 82)
    print("resolve_hollow_v7 — إشارتان (الماضي + عين المضارع المعتلّة) + معجم")
    print("=" * 82)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    confirmed, review, correct = [], [], 0
    print(f"\n{'الفعل':<7}{'الأصل':<7}{'الناتج':<7}{'المرحلة':<22}{'الإشارة'}")
    print("-" * 82)
    for lemma, truth in TEST:
        r = resolve(gen, lemma)
        letter = r["letter"] or "؟"
        ok = "✅" if r["letter"] == truth else ("🔍" if r["conf"] == "review" else "❌")
        if r["letter"] == truth: correct += 1
        (confirmed if r["conf"] == "confirmed" else review).append((lemma, truth, r))
        print(f"{lemma:<7}{truth:<7}{letter:<7}{r['stage']:<22}{r['sig']}  {ok}")
    n = len(TEST)
    print("-" * 82)
    print(f"مؤكَّد: {len(confirmed)} | مراجعة: {len(review)} | دقّة (مؤكَّد+معجم): {correct}/{n} = {100*correct//n}%")
    print("\n[للمراجعة]:", "، ".join(l for l, _, _ in review) or "(فارغ)")
    wrong = [(l, t, r['letter']) for l, t, r in confirmed if r['letter'] != t]
    print("[أخطاء في المؤكَّد]:", wrong or "لا يوجد ✅")

if __name__ == "__main__":
    _f = open("jawf_v7_output.txt", "w", encoding="utf-8")
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
