# -*- coding: utf-8 -*-
import sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
print("… استيراد CAMeL")
try:
    from camel_tools.disambig.mle import MLEDisambiguator
    from camel_tools.tokenizers.word import simple_word_tokenize
except Exception as e:
    print("فشل استيراد camel_tools:", e); raise SystemExit
print("… تحميل نموذج MLE (calima-msa) — قد يأخذ دقيقة")
try:
    mle = MLEDisambiguator.pretrained()
except Exception as e:
    print("فشل تحميل النموذج — غالبًا البيانات غير محمّلة.")
    print("الحلّ: شغّل في PowerShell:  venv\\Scripts\\camel_data -i light")
    print("الخطأ:", e); raise SystemExit

SENTS = [
    "خيم الحزن على مدينة المحمودية عقب وفاة عزة رمزي",
    "ضرب زلزال بنما",
    "حول الحادث فرحة كانت تنتظرها إلى مأساة",
    "أعادت إلى الواجهة الثمن الإنساني للاعتداءات",
]
for t in SENTS:
    toks = simple_word_tokenize(t)
    try:
        dis = mle.disambiguate(toks)
    except Exception as e:
        print("خطأ disambiguate:", e); continue
    diac=[]; pos=[]
    for d in dis:
        a = d.analyses[0].analysis if d.analyses else {}
        diac.append(a.get('diac', d.word)); pos.append(a.get('pos',''))
    print("="*64)
    print("إدخال :", t)
    print("CAMeL :", " ".join(diac))
    print("POS   :", " ".join(f"{w}:{p}" for w,p in zip(diac,pos)))
print("="*64)
