# -*- coding: utf-8 -*-
"""
resolve_hollow_v4.py — الخوارزمية الذهبيّة (مبنيّة على مخرجات CAMeL الفعلية)

المبدأ المثبَت بالبيانات:
  • حقل root من CAMeL يضع # مكان الحرف المعتلّ → عديم الفائدة للأصل.
  • تحليل الماضي (pattern/diac/caphi/lex/bw/stem) كلّه يُظهر الألف السطحيّة فقط.
  • الإشارة الوحيدة = الحرف الأوسط في صيغة المضارع المفرد المذكر المعلوم:
        يَفْعُل → و (واويّ)   |   يَفْعِل → ي (يائيّ)   |   يَفْعَل → ا (غامض)

المراحل (فلسفة: المؤكّد يُعتمد، المشكوك يُراجع):
  المرحلة 1: الحرف الأوسط من المضارع المعلوم.
             و/ي → مؤكَّد بثقة 100%.
             ا   → المرحلة 2.
  المرحلة 2: قائمة مغلقة مُحقَّقة لأفعال فَعِلَ يَفْعَلُ الجوف (تنمو بالتحقّق فقط).
             غير موجود → قائمة المراجعة اليدوية.

التشغيل:  .\\venv\\Scripts\\python.exe resolve_hollow_v4.py
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
    print("خطأ في استيراد CAMeL Tools:", e)
    sys.exit(1)

WAW, YA, ALIF = "و", "ي", "ا"
DIACS = set("ًٌٍَُِّْٰ")  # الحركات + الأليف الصغيرة

# المرحلة 2: قائمة مغلقة مُحقَّقة فقط (لا تخمين — تنمو بالتحقّق البصريّ/المصدر)
#            وزن فَعِلَ يَفْعَلُ الجوف: مضارعه ألف، فيُحسم بالمصدر.
HOLLOW_FaIL_VERIFIED = {
    "خاف": WAW,   # المصدر: خَوْف
    "نام": WAW,   # المصدر: نَوْم
    "هاب": YA,    # المصدر: هَيْبة
}

# مجموعة اختبار (الفعل, الأصل الصحيح, الجذر) — للتقييم فقط
TEST = [
    ("قال", WAW, "ق.و.ل"), ("باع", YA, "ب.ي.ع"), ("صام", WAW, "ص.و.م"),
    ("طال", WAW, "ط.و.ل"), ("دار", WAW, "د.و.ر"), ("كان", WAW, "ك.و.ن"),
    ("زاد", YA, "ز.ي.د"), ("خاف", WAW, "خ.و.ف"), ("نام", WAW, "ن.و.م"),
    ("مات", WAW, "م.و.ت"), ("طاب", YA, "ط.ي.ب"), ("هاب", YA, "ه.ي.ب"),
    ("سار", YA, "س.ي.ر"),
]

def strip_diac(text):
    return "".join(c for c in text if c not in DIACS)

def present_middle(generator, lemma):
    """يُرجع (الحرف الأوسط, صيغة المضارع) من المضارع المفرد المذكر المعلوم."""
    feats_list = [
        {"pos": "verb", "asp": "i", "mod": "i", "vox": "a",
         "per": "3", "gen": "m", "num": "s"},
        {"pos": "verb", "asp": "i", "vox": "a"},
        {"pos": "verb", "asp": "i"},
    ]
    for feats in feats_list:
        try:
            gens = generator.generate(lemma, feats)
        except Exception:
            continue
        cands = []
        for g in gens:
            if g.get("vox", "a") != "a":          # المعلوم فقط (لا المبنيّ للمجهول)
                continue
            bare = strip_diac(g.get("diac", ""))
            # المضارع المفرد المذكر لثلاثيّ أجوف: يبدأ بـ ي وطوله 4 حروف
            if bare.startswith("ي") and len(bare) == 4:
                cands.append(bare)
        # فضّل الصيغة التي وسطها معتلّ صريح (و/ي) إن وُجدت، وإلا خذ أوّل صيغة
        for b in cands:
            if b[2] in (WAW, YA):
                return b[2], b
        if cands:
            return cands[0][2], cands[0]
    return None, None

def resolve(generator, lemma):
    """يُرجع dict بالنتيجة: letter, confidence, stage, present."""
    mid, pres = present_middle(generator, lemma)
    # المرحلة 1
    if mid == WAW:
        return {"letter": WAW, "conf": "confirmed", "stage": "present_waw", "present": pres}
    if mid == YA:
        return {"letter": YA, "conf": "confirmed", "stage": "present_ya", "present": pres}
    # المرحلة 2 (مضارعه ألف أو تعذّر)
    if lemma in HOLLOW_FaIL_VERIFIED:
        return {"letter": HOLLOW_FaIL_VERIFIED[lemma], "conf": "confirmed",
                "stage": "closed_list_faIl", "present": pres}
    # المرحلة 3: مراجعة يدوية
    return {"letter": None, "conf": "review", "stage": "needs_review", "present": pres}

def main():
    print("=" * 74)
    print("resolve_hollow_v4 — نتائج الحلّ على مجموعة الاختبار")
    print("=" * 74)
    db_g = MorphologyDB.builtin_db(flags="g")
    generator = Generator(db_g)

    confirmed, review = [], []
    correct = 0
    print(f"\n{'الفعل':<7}{'المضارع':<10}{'الأصل':<7}{'الناتج':<7}{'المرحلة':<20}{'الحكم'}")
    print("-" * 74)
    for lemma, truth, root in TEST:
        r = resolve(generator, lemma)
        letter = r["letter"] if r["letter"] else "؟"
        ok = "✅" if r["letter"] == truth else ("🔍 مراجعة" if r["conf"] == "review" else "❌")
        if r["letter"] == truth:
            correct += 1
        if r["conf"] == "confirmed":
            confirmed.append((lemma, r["letter"], r["stage"]))
        else:
            review.append((lemma, r["present"]))
        print(f"{lemma:<7}{str(r['present']):<10}{truth:<7}{letter:<7}{r['stage']:<20}{ok}")

    n = len(TEST)
    print("-" * 74)
    print(f"مؤكَّد: {len(confirmed)}   |   للمراجعة: {len(review)}")
    print(f"الدقّة على المؤكَّد + المراجعة الصحيحة: {correct}/{n} = {100*correct//n}%")
    print("\nملفّ المؤكَّد (يُعتمد آليًا):")
    for lemma, letter, stage in confirmed:
        print(f"   {lemma} → {letter}  ({stage})")
    print("\nملفّ المراجعة اليدوية (يُعرَض على الإنسان):")
    if review:
        for lemma, pres in review:
            print(f"   {lemma}  (مضارعه {pres} — ألف غامضة، يحتاج المصدر)")
    else:
        print("   (فارغ)")

if __name__ == "__main__":
    _f = open("jawf_v4_output.txt", "w", encoding="utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8") if False else sys.stdout
    class _Tee:
        def __init__(self, *s): self.s = s
        def write(self, x):
            for st in self.s:
                try: st.write(x)
                except Exception: pass
        def flush(self):
            for st in self.s:
                try: st.flush()
                except Exception: pass
    sys.stdout = _Tee(sys.stdout, _f)
    sys.stderr = sys.stdout
    try:
        main()
    finally:
        _f.flush(); _f.close()
