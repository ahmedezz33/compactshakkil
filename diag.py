# -*- coding: utf-8 -*-
"""يطبع كلَّ مرحلةٍ (نموذج خام → خط المعالجة → نقحرة → نصّ edge) لتحديد مصدر أيّ خطأ."""
import sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

SENTS = [
    "في الأسبوع السابق ضرب زلزال بنما",
    "مص الطفل ليده سلوك طبيعي يبدأ في الرحم ويعد وسيلة للتهدئة والاكتشاف",
    "الاكتشاف الاحتياجات الاكتساب الانتشار",
    "الحمد لله رب العالمين",
    "قال تعالى الحمد لله رب العالمين ثم دعا",
]
import diac_pipeline
INF = diac_pipeline._inf()
import g2p
from pronounce import edge_prepare
for sent in SENTS:
    raw  = INF.diacritize_partial(sent)              # مخرجُ النموذجِ الخام (respect)
    full = diac_pipeline.diacritize(sent, True)[0]    # بعد خطِّ المعالجةِ الكامل
    try: _ipa, lat = g2p.phonemize(full, "waqf")
    except Exception as e: lat = f"(خطأ نقحرة: {e})"
    try: spoken = edge_prepare(full, mode="waqf")
    except Exception as e: spoken = f"(خطأ: {e})"
    print("="*64)
    print("الإدخال      :", sent)
    print("النموذجُ الخام :", raw)
    print("بعدَ المعالجة  :", full)
    print("النقحرة       :", lat)
    print("نصُّ edge      :", spoken)
print("="*64)
