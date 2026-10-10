# -*- coding: utf-8 -*-
"""
jawf_clitic_probe.py — نواة طبقة فكّ التباس اللواصق (ARNS).

الفكرة: بعض الكلمات يقطّعها CAMeL دائمًا بلاصقة بادئة (كـ/بـ/لـ/فـ/وـ/سـ)،
فلا يعطي تحليلًا ككلمة كاملة — مع أنّ الحرف الأوّل قد يكون **أصليًّا**.
مثال: كيود → كـ+يود (تشبيه) فقط، وتفوته كَيُود (فَعُول من الكَيْد، ك.ي.د).

الطبقة:
  • تفحص هل ثمّة تحليل ككلمة كاملة (بلا لاصقة بادئة: prc0..prc3 = 0).
  • إن كانت **كل** التحليلات بلاصقة بادئة → تُعلَّم الكلمة كـ"مرشّحة لأصل الحرف الأوّل"
    وتُحال لطبقة الاسترداد/المراجعة.
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

DIAC = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIAC)

PRC = ["prc0", "prc1", "prc2", "prc3"]

# كلمات اختبار: ملتبسة (حرفها الأوّل قد يكون أصليًّا) + ضوابط (كلمات كاملة)
WORDS = [
    ("كيود", "ملتبسة؟ (كَيُود فَعُول من ك.ي.د / كـ+يود)"),
    ("كواكب", "ضابط — كلمة كاملة (ك أصليّة)"),
    ("كمال", "ضابط — كلمة كاملة"),
    ("لسان", "ضابط — كلمة كاملة (ل أصليّة)"),
    ("بيوت", "ضابط — كلمة كاملة (ب أصليّة)"),
    ("كتابه", "لاصقة حقيقية متوقّعة أحيانًا"),
    ("وريد", "ملتبسة؟ (و أصليّة و.ر.د / وـ+ريد)"),
    ("سلام", "ضابط — كلمة كاملة (س أصليّة)"),
]


def whole_word(a):
    """تحليل ككلمة كاملة: بلا أيّ لاصقة بادئة."""
    return all(str(a.get(f, "0")) in ("0", "") for f in PRC)


def probe(an, word):
    analyses = an.analyze(sd(word))
    whole = [a for a in analyses if whole_word(a)]
    clitic = [a for a in analyses if not whole_word(a)]
    flagged = bool(analyses) and not whole
    return analyses, whole, clitic, flagged


def main():
    an = Analyzer(MorphologyDB.builtin_db(flags="a"))
    print("=" * 78)
    print("طبقة فكّ التباس اللواصق — نواة")
    print("=" * 78)
    for word, note in WORDS:
        analyses, whole, clitic, flagged = probe(an, word)
        tag = "⚠️ مرشّحة (حرفها الأوّل قد يكون أصليًّا → استرداد/مراجعة)" if flagged \
              else "✅ لها تحليل ككلمة كاملة"
        print(f"\n▌ {word}   [{note}]")
        print(f"   تحليلات: {len(analyses)} | كاملة: {len(whole)} | بلاصقة: {len(clitic)}")
        print(f"   {tag}")
        # عيّنة من الجذور/المعاني
        for a in analyses[:3]:
            kind = "كاملة" if whole_word(a) else f"لاصقة({a.get('prc0','')})"
            print(f"      [{kind}] root={a.get('root',''):<8} {str(a.get('gloss',''))[:36]}")


if __name__ == "__main__":
    _f = open("jawf_clitic_output.txt", "w", encoding="utf-8")
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
