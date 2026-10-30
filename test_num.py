# -*- coding: utf-8 -*-
import sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
print("… تحميل النموذج (قد يأخذ دقيقة)")
import app_teach as A
from pronounce import edge_prepare
SENTS = [
    "البالغة من العمر 28 عامًا",
    "ارتفعت النسبة إلى 7.5 بالمئة عام 2026",
    "بتاريخ 15-4-1448 حضر 1250 شخصًا",
    "خيم الحزن على مدينة المحمودية عقب وفاة عزة رمزي",
]
for t in SENTS:
    dia,_ = A.diacritize(t)
    try: spoken = edge_prepare(dia, mode="waqf")
    except Exception as e: spoken = f"(خطأ: {e})"
    print("="*64)
    print("إدخال :", t)
    print("تشكيل :", dia)
    print("نطق   :", spoken)
print("="*64)
