# -*- coding: utf-8 -*-
"""
resolve_hollow_v9.py — الخوارزمية الذهبيّة (المضارع شاهد أساسيّ + كشف أعمق)

تطوير v8→v9 (بعد تشخيص الحالات الحديّة):
  • عين المضارع المعتلّة تقرأ نوع القراءة مباشرة:
        و → قراءة واويّة (يَفْعُل)  |  ي → قراءة يائيّة (يَفْعِل)  |  ا → صنف فَعِلَ يَفْعَلُ
  • تعدّد المعتلّ في المضارع (≥2) = متجانس بجذرين (يُنقذ كاد: يكاد+يكيد).
  • الماضي احتياطيّ فقط حين يفشل توليد المضارع (يُنقذ هان: مضارعه يهون=و).

منطق القرار:
  عين المضارع (مجموعة المعتلّ):
     |set| ≥ 2                → متجانس → فصل سياقيّ
     {و}                     → واو  [قاعدة]
     {ي}                     → ياء  [قاعدة]
     {ا}                     → صنف الألف → معجم أو مراجعة
     {} (تعذّر المضارع):
         ماضٍ {ضمّة}          → واو  [احتياطيّ]
         ماضٍ {ضمّة,كسرة}     → متجانس
         غير ذلك             → مراجعة
"""
import sys
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

# معجم مُحقَّق لصنف الألف (فَعِلَ يَفْعَلُ) — يُحسم بالمصدر لا بالتصريف
ALIF_HOLLOW_LEX = {"خاف": WAW, "نام": WAW, "شاء": YA, "هاب": YA}

def present_weak_set(gen, lemma):
    """مجموعة الحرف الأوسط المعتلّ في صيغ المضارع المعلوم (3م مفرد، 4 حروف)."""
    try:
        g = gen.generate(lemma, {"pos": "verb", "asp": "i"})
    except Exception:
        return set()
    ws = set()
    for a in g:
        if a.get("vox", "a") != "a":
            continue
        diac = a.get("diac", "")
        if not diac.startswith("يَ"):
            continue
        bare = sd(diac)
        if len(bare) == 4 and bare[2] in WEAK:
            ws.add(bare[2])
    return ws

def past1s_vowels(gen, lemma):
    try:
        g = gen.generate(lemma, {"pos": "verb", "asp": "p", "vox": "a", "per": "1", "num": "s"})
    except Exception:
        return set()
    vs = set()
    for a in g:
        f = a.get("diac", "")
        if len(f) >= 2 and f[1] in (DAMMA, KASRA):
            vs.add(f[1])
    return vs

def resolve(gen, lemma):
    pw = present_weak_set(gen, lemma)
    if len(pw) >= 2:
        return {"letter": "و/ي", "conf": "homograph", "stage": "متجانس (تعدّد عين المضارع)"}
    if pw == {WAW}:
        return {"letter": WAW, "conf": "confirmed", "stage": "مضارع عينه واو → واو"}
    if pw == {YA}:
        return {"letter": YA, "conf": "confirmed", "stage": "مضارع عينه ياء → ياء"}
    if pw == {ALIF}:
        if lemma in ALIF_HOLLOW_LEX:
            return {"letter": ALIF_HOLLOW_LEX[lemma], "conf": "confirmed", "stage": "صنف الألف: معجم"}
        return {"letter": None, "conf": "review", "stage": "صنف الألف: مراجعة"}
    # المضارع فارغ → احتياطيّ من الماضي
    pv = past1s_vowels(gen, lemma)
    if pv == {DAMMA, KASRA}:
        return {"letter": "و/ي", "conf": "homograph", "stage": "متجانس (ماضٍ احتياطيّ)"}
    if pv == {DAMMA}:
        return {"letter": WAW, "conf": "confirmed", "stage": "ماضٍ ضمّة (احتياطيّ) → واو"}
    return {"letter": None, "conf": "review", "stage": "لا إشارة → مراجعة"}

# مجموعة اختبار: أساسيّة + حديّة (لإظهار الإنقاذ والكشف)
TEST = [
    ("قال", WAW), ("باع", YA), ("خاف", WAW), ("نام", WAW), ("هاب", YA), ("شاء", YA),
    ("سار", YA), ("زاد", YA), ("مات", WAW), ("كان", WAW),
    # حديّة
    ("هان", WAW),   # كان مراجعة في v8 → يُنقذ (مضارع يهون)
    ("كاد", None),  # كان مراجعة → يُكشف متجانسًا (يكاد+يكيد)
    ("خال", None),  # صنف ألف → مراجعة (صحيح)
    ("طاف", None), ("زال", None), ("مار", None),   # متجانسات
    ("غار", WAW), ("حاك", WAW), ("جار", WAW),      # حدّ CAMeL (عين مضارع {و} فقط)
    ("ضاع", None), ("شاب", None), ("نال", None), ("زاغ", None), ("حار", None),
]

def main():
    print("=" * 82)
    print("resolve_hollow_v9 — المضارع شاهد أساسيّ")
    print("=" * 82)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    c = {"confirmed": 0, "homograph": 0, "review": 0}
    print(f"\n{'الفعل':<7}{'المتوقّع':<9}{'الناتج':<7}{'المرحلة':<30}{'حكم'}")
    print("-" * 82)
    for lemma, gold in TEST:
        r = resolve(gen, lemma)
        c[r["conf"]] += 1
        letter = r["letter"] or "؟"
        if gold in (WAW, YA):
            mark = "✅" if r["letter"] == gold else ("🔍" if r["conf"] in ("review", "homograph") else "❌")
        else:
            mark = "🔀" if r["conf"] == "homograph" else ("🔍" if r["conf"] == "review" else "—")
        print(f"{lemma:<7}{str(gold or '—'):<9}{letter:<7}{r['stage']:<30}{mark}")
    print("-" * 82)
    print(f"مؤكَّد={c['confirmed']}  متجانس={c['homograph']}  مراجعة={c['review']}")

if __name__ == "__main__":
    _f = open("jawf_v9_output.txt", "w", encoding="utf-8")
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
