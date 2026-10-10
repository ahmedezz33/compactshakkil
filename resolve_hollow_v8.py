# -*- coding: utf-8 -*-
"""
resolve_hollow_v8.py — الخوارزمية الذهبيّة (كشف المتجانسات)

إصلاح v7→v8 (بعد التشخيص):
  CAMeL يولّد صيغتَي الماضي معًا للفعل المتجانس بجذرين:
     ضاع → ضُعْتُ (ض.و.ع) + ضِعْتُ (ض.ي.ع)
  كانت v7 تأخذ أوّل صيغة فقط → تصنيف اعتباطيّ. الإصلاح: نجمع كل الحركات.

منطق القرار:
  حركات الماضي = {ضمّة} فقط              → واو            [قاعدة، يقين]
  حركات الماضي = {كسرة} فقط:
       عين المضارع ياء                    → ياء            [قاعدة، يقين]
       عين المضارع واو                    → واو            [نادر]
       عين المضارع ألف → صنف فَعِلَ:
             في المعجم → يُعتمد ؛ غير ذلك → مراجعة
  حركات الماضي = {ضمّة, كسرة} معًا       → متجانس بجذرين (و/ي) → فصل سياقيّ
  لا حركات (فراغ توليد)                  → مراجعة (ثغرة CAMeL)
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

TEST = [
    ("قال",WAW),("باع",YA),("صام",WAW),("طال",WAW),("دار",WAW),("كان",WAW),
    ("زاد",YA),("خاف",WAW),("نام",WAW),("مات",WAW),("طاب",YA),("هاب",YA),
    ("سار",YA),("شاء",YA),
    # متجانسات (المتوقّع: كشف تعدّد الجذر)
    ("ضاع",None),("شاب",None),("نال",None),("زاغ",None),("حار",None),
]

def past1s_vowels(gen, lemma):
    """مجموعة حركات الحرف الأوّل عبر كل صيغ ماضي المتكلّم المولّدة."""
    try:
        g = gen.generate(lemma, {"pos":"verb","asp":"p","vox":"a","per":"1","num":"s"})
    except Exception:
        return set(), []
    vowels, forms = set(), []
    for a in g:
        f = a.get("diac","")
        forms.append(f)
        if len(f) >= 2 and f[1] in (DAMMA, KASRA):
            vowels.add(f[1])
    return vowels, sorted(set(forms))

def present_middle(gen, lemma):
    try:
        g = gen.generate(lemma, {"pos":"verb","asp":"i"})
    except Exception:
        return None
    for a in g:
        if a.get("vox","a") != "a": continue
        diac = a.get("diac","")
        if not diac.startswith("يَ"): continue
        bare = sd(diac)
        if len(bare) == 4 and bare[2] in WEAK:
            return bare[2]
    return None

def resolve(gen, lemma):
    vowels, forms = past1s_vowels(gen, lemma)
    mid = present_middle(gen, lemma)
    sig = f"ماضٍ={forms} | عين={mid or '—'}"

    if vowels == {DAMMA, KASRA}:
        return {"letter": "و/ي", "conf": "homograph", "stage": "متجانس بجذرين → فصل سياقيّ", "sig": sig}
    if vowels == {DAMMA}:
        return {"letter": WAW, "conf": "confirmed", "stage": "ضمّة→واو", "sig": sig}
    if vowels == {KASRA}:
        if mid == YA:  return {"letter": YA,  "conf":"confirmed","stage":"كسرة+ياء→ياء","sig":sig}
        if mid == WAW: return {"letter": WAW, "conf":"confirmed","stage":"كسرة+واو→واو","sig":sig}
        if lemma in ALIF_HOLLOW_LEX:
            return {"letter": ALIF_HOLLOW_LEX[lemma], "conf":"confirmed","stage":"صنف الألف: معجم","sig":sig}
        return {"letter": None, "conf":"review","stage":"صنف الألف: مراجعة","sig":sig}
    return {"letter": None, "conf":"review","stage":"فراغ توليد → مراجعة","sig":sig}

def main():
    print("=" * 88)
    print("resolve_hollow_v8 — كشف المتجانسات + قاعدة صرفية بإشارتين")
    print("=" * 88)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))
    counts = {"confirmed":0,"homograph":0,"review":0}
    correct = total_labeled = 0
    print(f"\n{'الفعل':<7}{'المتوقّع':<9}{'الناتج':<8}{'الحالة':<11}{'المرحلة':<26}{'حكم'}")
    print("-"*88)
    for lemma, truth in TEST:
        r = resolve(gen, lemma)
        counts[r["conf"]] += 1
        if truth is not None:
            total_labeled += 1
            if r["letter"] == truth: correct += 1
        if truth is None:
            mark = "🔀" if r["conf"]=="homograph" else "🔍"
        else:
            mark = "✅" if r["letter"]==truth else ("🔍" if r["conf"] in ("review","homograph") else "❌")
        print(f"{lemma:<7}{str(truth or '—'):<9}{str(r['letter'] or '؟'):<8}{r['conf']:<11}{r['stage']:<26}{mark}")
    print("-"*88)
    print(f"مؤكَّد={counts['confirmed']}  متجانس={counts['homograph']}  مراجعة={counts['review']}")
    print(f"دقّة على المُسمّى (المؤكَّد): {correct}/{total_labeled}")
    print(f"\nتنبيه: المتجانسات (ضاع/شاب/نال/زاغ/حار) يجب أن تظهر 🔀 لا خطأ.")

if __name__ == "__main__":
    _f = open("jawf_v8_output.txt","w",encoding="utf-8")
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
