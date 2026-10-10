# -*- coding: utf-8 -*-
"""
resolve_hollow_v10.py — الخوارزمية الذهبيّة (اتّحاد الشاهدين: ماضٍ + مضارع)

المبدأ (كما صاغه أحمد): الماضي والمضارع شاهدان متكافئان، لا أحدهما تابع.
نجمع أدلّة القراءات من الاثنين معًا:

  دليل "واو"        : ضمّة في الماضي  أو  عين مضارع = و
  دليل "ياء" (يفعِل): عين مضارع = ي
  دليل "ألف" (فَعِلَ): عين مضارع = ا
  دليل "كسرة؟"      : كسرة في الماضي لم يكشف المضارع نوعها (ياء أم ألف)

القرار:
  عدد القراءات ≥ 2            → متجانس بجذرين → فصل سياقيّ
  {واو}                      → واو  [قاعدة]
  {ياء}                      → ياء  [قاعدة]
  {ألف}                      → صنف فَعِلَ → معجم أو مراجعة
  {كسرة؟}                    → كسرة بلا مضارع مميِّز → مراجعة
  {} (لا شيء)                → مراجعة

يمسك: كاد (بالمضارع {ا,ي})، حار (بالماضي {ضمّة,كسرة})، هان (مضارع و رغم فراغ الماضي).
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

ALIF_HOLLOW_LEX = {"خاف": WAW, "نام": WAW, "شاء": YA, "هاب": YA}

def present_weak_set(gen, lemma):
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
    pv = past1s_vowels(gen, lemma)
    readings = set()
    if DAMMA in pv or WAW in pw:
        readings.add("waw")
    if YA in pw:
        readings.add("ya")
    if ALIF in pw:
        readings.add("alif")
    if KASRA in pv and "ya" not in readings and "alif" not in readings:
        readings.add("kasra?")

    sig = f"ماضٍ={sorted(pv)} مضارع={sorted(pw)}"
    if len(readings) >= 2:
        return {"letter": "و/ي", "conf": "homograph", "stage": "متجانس (اتّحاد الشاهدين)", "sig": sig}
    if readings == {"waw"}:
        return {"letter": WAW, "conf": "confirmed", "stage": "واو", "sig": sig}
    if readings == {"ya"}:
        return {"letter": YA, "conf": "confirmed", "stage": "ياء", "sig": sig}
    if readings == {"alif"}:
        if lemma in ALIF_HOLLOW_LEX:
            return {"letter": ALIF_HOLLOW_LEX[lemma], "conf": "confirmed", "stage": "صنف الألف: معجم", "sig": sig}
        return {"letter": None, "conf": "review", "stage": "صنف الألف: مراجعة", "sig": sig}
    if readings == {"kasra?"}:
        return {"letter": None, "conf": "review", "stage": "كسرة بلا مضارع مميِّز → مراجعة", "sig": sig}
    return {"letter": None, "conf": "review", "stage": "لا إشارة → مراجعة", "sig": sig}

TEST = [
    ("قال", WAW), ("باع", YA), ("خاف", WAW), ("نام", WAW), ("هاب", YA), ("شاء", YA),
    ("سار", YA), ("زاد", YA), ("مات", WAW), ("كان", WAW),
    ("هان", WAW), ("كاد", None), ("خال", None),
    ("طاف", None), ("زال", None), ("مار", None), ("حار", None),
    ("غار", WAW), ("حاك", WAW), ("جار", WAW),
    ("ضاع", None), ("شاب", None), ("نال", None), ("زاغ", None),
]

def main():
    print("=" * 88)
    print("resolve_hollow_v10 — اتّحاد الشاهدين (ماضٍ + مضارع)")
    print("=" * 88)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    c = {"confirmed": 0, "homograph": 0, "review": 0}
    print(f"\n{'الفعل':<7}{'المتوقّع':<9}{'الناتج':<7}{'المرحلة':<26}{'الإشارة':<22}{'حكم'}")
    print("-" * 88)
    for lemma, gold in TEST:
        r = resolve(gen, lemma)
        c[r["conf"]] += 1
        letter = r["letter"] or "؟"
        if gold in (WAW, YA):
            mark = "✅" if r["letter"] == gold else ("🔍" if r["conf"] in ("review", "homograph") else "❌")
        else:
            mark = "🔀" if r["conf"] == "homograph" else ("🔍" if r["conf"] == "review" else "—")
        print(f"{lemma:<7}{str(gold or '—'):<9}{letter:<7}{r['stage']:<26}{r['sig']:<22}{mark}")
    print("-" * 88)
    print(f"مؤكَّد={c['confirmed']}  متجانس={c['homograph']}  مراجعة={c['review']}")

if __name__ == "__main__":
    _f = open("jawf_v10_output.txt", "w", encoding="utf-8")
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
