# -*- coding: utf-8 -*-
import sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
print("… تحميل النموذج + محلّل CAMeL")
import app_teach as A
import camel_snap
SENTS = [
    "خيم الحزن على مدينة المحمودية عقب وفاة عزة رمزي",
    "ضرب زلزال بنما",
    "حول الحادث فرحة كانت تنتظرها إلى مأساة",
    "أعادت إلى الواجهة الثمن الإنساني للاعتداءات",
    "ذهب الطالب المجتهد إلى المدرسة",
]
for t in SENTS:
    dia,_ = A.diacritize(t)
    snp = camel_snap.snap_text(dia)
    print("="*64)
    print("إدخال :", t)
    print("BERT  :", dia)
    print("+snap :", snp)
    if snp!=dia: print("   (تغيّرت كلماتٌ ↑)")
print("="*64)
