# -*- coding: utf-8 -*-
"""
jawf_context_test.py — هل يحسم السياق المتجانسات؟ (MLEDisambiguator)

لكل فعل متجانس: جملتان تفرضان معنيين مختلفين. نمرّر الجملة على
MLEDisambiguator ونطبع القراءة المختارة للكلمة الهدف (الجذر + التشكيل + المعنى).
السؤال: هل يتغيّر المعنى المختار بتغيّر الجملة؟

ملاحظة: يحتاج بيانات MLE. إن فشل التحميل، نزّلها:
    camel_data -i disambig-mle-calima-msa-r13
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
try:
    from camel_tools.disambig.mle import MLEDisambiguator
    from camel_tools.tokenizers.word import simple_word_tokenize
except Exception as e:
    print("خطأ استيراد CAMeL:", e); sys.exit(1)

DIAC = set("ًٌٍَُِّْٰ")
def sd(t): return "".join(c for c in t if c not in DIAC)

# (الكلمة الهدف, الجملة, المعنى المقصود)
CASES = [
    ("ضاع", "ضاع الكتاب مني في الطريق", "فُقد (ض.ي.ع)"),
    ("ضاع", "ضاع عطر المسك في أرجاء البيت", "فاح/انتشر (ض.و.ع)"),
    ("طاف", "طاف الحجاج حول الكعبة سبعا", "دار (ط.و.ف)"),
    ("طاف", "طاف بي خيال الحبيب ليلا", "زار طيفا (ط.ي.ف)"),
    ("حار", "حار الرجل في جواب السؤال", "تحيّر (ح.ي.ر)"),
    ("حار", "حار الماء ثم عاد الى مجراه", "رجع (ح.و.ر)"),
    ("مار", "مار القوم في الطعام والزاد", "جلب الميرة (م.ي.ر)"),
    ("مار", "مار الشيء يمور حركة", "تحرّك (م.و.ر)"),
    ("زاغ", "زاغ البصر عن الهدف", "مال/انحرف (ز.ي.غ)"),
    ("كيود", "فلان كيود ماكر يدبر المكايد", "صيغة مبالغة (ك.ي.د) — اختبار الثغرة"),
]


def target_reading(mle, sentence, target):
    toks = simple_word_tokenize(sentence)
    dis = mle.disambiguate(toks)
    for d in dis:
        if sd(d.word) == sd(target):
            if not d.analyses:
                return None
            a = d.analyses[0].analysis
            return (a.get("root", ""), a.get("diac", ""),
                    a.get("lex", ""), str(a.get("gloss", ""))[:40])
    return None


def main():
    print("=" * 80)
    print("اختبار الحسم بالسياق — MLEDisambiguator")
    print("=" * 80)
    try:
        mle = MLEDisambiguator.pretrained()
    except Exception as e:
        print("\n❌ تعذّر تحميل نموذج MLE. نزّل البيانات ثمّ أعد التشغيل:")
        print("   camel_data -i disambig-mle-calima-msa-r13")
        print(f"\n(الخطأ: {e})")
        return

    for target, sentence, meaning in CASES:
        r = target_reading(mle, sentence, target)
        print(f"\n▌ «{target}» في: {sentence}")
        print(f"  المقصود: {meaning}")
        if r:
            print(f"  اختار CAMeL: جذر={r[0]}  تشكيل={r[1]}  لَمّة={r[2]}  معنى={r[3]}")
        else:
            print("  ⚠️ لم يُحلَّل / لا قراءة")


if __name__ == "__main__":
    _f = open("jawf_context_output.txt", "w", encoding="utf-8")
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
