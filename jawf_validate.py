# -*- coding: utf-8 -*-
"""
jawf_validate.py — تحقّق موسّع لخوارزمية v7 على ~43 فعلاً أجوف.

يقيس ثلاثة أشياء (لا رقمًا واحدًا مضلّلاً):
  1) دقّة القاعدة الصرفية الخالصة على صنف فَعَلَ (يجب أن تبقى عالية جدًا).
  2) حِمل المراجعة: كم فعلاً يقع في صنف الألف (فَعِلَ يَفْعَلُ).
  3) تغطية المعجم للصنف الغامض.

⚠️ التسميات الذهبية (الأصل المتوقّع) مقترحة من الصرف وتحتاج تأكيد أحمد.
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

# (الفعل, الأصل المتوقّع) — مقترح صرفيّ يحتاج تأكيدك
GOLD = [
    ("قال",WAW),("قام",WAW),("صام",WAW),("دام",WAW),("عاد",WAW),("زار",WAW),
    ("فاز",WAW),("دار",WAW),("كان",WAW),("مات",WAW),("نام",WAW),("خاف",WAW),
    ("تاب",WAW),("ذاق",WAW),("طاف",WAW),("قاد",WAW),("ثار",WAW),("لام",WAW),
    ("خان",WAW),("صان",WAW),("عام",WAW),("كاد",WAW),("ناح",WAW),
    ("باع",YA),("زاد",YA),("طاب",YA),("سار",YA),("صار",YA),("طار",YA),
    ("غاب",YA),("عاش",YA),("سال",YA),("ضاع",YA),("شاب",YA),("هاب",YA),
    ("شاء",YA),("دان",YA),("حان",YA),("زان",YA),("هام",YA),("نال",YA),
    ("فاض",YA),("زاغ",YA),
]
# أفعال بلا تسمية (لقياس التوزيع فقط)
EXTRA = ["حار","جاد","ساد","هان","لاح","ماج","غار","باد","حاز","راح"]

def past1s_vowel(gen, lemma):
    try:
        g = gen.generate(lemma, {"pos":"verb","asp":"p","vox":"a","per":"1","num":"s"})
    except Exception:
        return None, None
    for a in g:
        f = a.get("diac","")
        if len(f) >= 2 and f[1] in (DAMMA, KASRA):
            return f[1], f
    return None, (g[0].get("diac","") if g else None)

def present_middle(gen, lemma):
    try:
        g = gen.generate(lemma, {"pos":"verb","asp":"i"})
    except Exception:
        return None, None
    for a in g:
        if a.get("vox","a") != "a":
            continue
        diac = a.get("diac","")
        if not diac.startswith("يَ"):
            continue
        bare = sd(diac)
        if len(bare) == 4 and bare[2] in WEAK:
            return bare[2], diac
    return None, None

def resolve(gen, lemma):
    pv, pform = past1s_vowel(gen, lemma)
    mid, _ = present_middle(gen, lemma)
    if pv == DAMMA:
        return WAW, "rule", "ضمّة→واو"
    if pv == KASRA:
        if mid == YA:  return YA, "rule", "كسرة+ياء→ياء"
        if mid == WAW: return WAW, "rule", "كسرة+واو→واو"
        if lemma in ALIF_HOLLOW_LEX:
            return ALIF_HOLLOW_LEX[lemma], "lexicon", "صنف الألف: معجم"
        return None, "review", "صنف الألف: مراجعة"
    return None, "review", "تعذّر الماضي"

def main():
    print("=" * 84)
    print("jawf_validate — تحقّق موسّع (v7) على ~43 فعلاً + 10 بلا تسمية")
    print("=" * 84)
    gen = Generator(MorphologyDB.builtin_db(flags="g"))

    buckets = {"rule": 0, "lexicon": 0, "review": 0}
    rule_correct = rule_total = 0
    lex_correct = lex_total = 0
    wrong, review_q = [], []

    print(f"\n{'الفعل':<7}{'المتوقّع':<9}{'الناتج':<8}{'المصدر':<9}{'المرحلة':<22}{'حكم'}")
    print("-" * 84)
    for lemma, truth in GOLD:
        letter, src, stage = resolve(gen, lemma)
        buckets[src] += 1
        if src == "rule":
            rule_total += 1
            if letter == truth: rule_correct += 1
            else: wrong.append((lemma, truth, letter, stage))
        elif src == "lexicon":
            lex_total += 1
            if letter == truth: lex_correct += 1
            else: wrong.append((lemma, truth, letter, stage))
        else:
            review_q.append(lemma)
        mark = "✅" if letter == truth else ("🔍" if src == "review" else "❌")
        print(f"{lemma:<7}{truth:<9}{str(letter or '؟'):<8}{src:<9}{stage:<22}{mark}")

    print("\n" + "-" * 84 + "\n[أفعال بلا تسمية — للتوزيع فقط]")
    for lemma in EXTRA:
        letter, src, stage = resolve(gen, lemma)
        buckets[src] += 1
        if src == "review": review_q.append(lemma)
        print(f"{lemma:<7}{'—':<9}{str(letter or '؟'):<8}{src:<9}{stage:<22}")

    total = len(GOLD) + len(EXTRA)
    print("\n" + "=" * 84)
    print("الملخّص")
    print("=" * 84)
    print(f"التوزيع: قاعدة={buckets['rule']}  معجم={buckets['lexicon']}  مراجعة={buckets['review']}  (من {total})")
    if rule_total:
        print(f"دقّة القاعدة الصرفية الخالصة: {rule_correct}/{rule_total} = {100*rule_correct//rule_total}%  ← المساهمة القابلة للتعميم")
    if lex_total:
        print(f"دقّة المعجم: {lex_correct}/{lex_total}")
    print(f"حِمل المراجعة اليدوية: {len(review_q)} فعلاً → {'، '.join(review_q)}")
    print(f"\n[أخطاء القاعدة/المعجم — الأهمّ للفحص]: {wrong or 'لا يوجد ✅'}")

if __name__ == "__main__":
    _f = open("jawf_validate_output.txt", "w", encoding="utf-8")
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
