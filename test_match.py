# -*- coding: utf-8 -*-
"""يقارن تشكيلَ تطبيقك الأصليّ (app_teach) بتشكيل الـ API (diac_pipeline) حرفًا بحرف."""
import sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

SAMPLES = [
    "أغلقت السلطات المطار بسبب سوء الأحوال الجوية",
    "الاحتياجات الأساسية للإنسان كثيرة",
    "قال الرجل كلاما طيبا",
    "إن العلم نور",
    "﴿الحمد لله رب العالمين﴾",
    "قال تعالى ﴿وما خلقت الجن والإنس إلا ليعبدون﴾ في سورة الذاريات",
    "ارتفعت النسبة إلى 7.7 بالمئة هذا العام",
]

import diac_pipeline
print("… تحميلُ تطبيقِك الأصليِّ (app_teach) للمقارنة — قد يستغرقُ دقيقةً")
try:
    import app_teach as A
    have = True
except Exception as e:
    have = False
    print("تعذّرَ استيرادُ app_teach:", e)

ok = True
print("="*60)
for t in SAMPLES:
    api = diac_pipeline.diacritize(t, True)[0]
    if have:
        app = A.diacritize(t, True)[0]
        same = (app == api)
        ok = ok and same
        print(("[مطابق]" if same else "[مختلف]"), t)
        if not same:
            print("   التطبيق:", app)
            print("   الـAPI :", api)
    else:
        print("API:", t, "=>", api)
print("="*60)
if have:
    print("النتيجةُ النهائيّة:", "كلُّ الجُمَلِ متطابقةٌ تمامًا ✅" if ok else "توجد فروقٌ — انظر أعلاه ⚠️")
else:
    print("لم تُجرَ المقارنةُ (app_teach لم يُستورَد) — راجِعْ مخرجاتِ الـAPI يدويًّا")
