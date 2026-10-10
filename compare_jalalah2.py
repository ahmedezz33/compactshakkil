# -*- coding: utf-8 -*-
"""compare_jalalah2.py — دفعةٌ ثانية: صيغٌ جديدةٌ لتفخيم لفظ الجلالة (بعد فتح)
لم تُختبَر سابقًا. الملفّاتُ في recordings/jalalah_test2/."""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")
OUT=os.path.join("recordings","jalalah_test2"); os.makedirs(OUT,exist_ok=True)

CASES={
 "A6_خنجرية_ضمة":     "هُوَ اللّٰهُ أَحَدٌ",     # ألف خنجريّة + ضمّة
 "A7_ألف_صريحة":       "هُوَ اللَاهُ أَحَدٌ",     # لام+ألف صريحة+ضمّة (لاه)
 "A8_وصل_شدة_ضمة":     "هُوَ ٱللَّهُ أَحَدٌ",     # ألف وصل
 "A9_خنجرية_بلا_حركة": "هُوَ اللّٰه أَحَدٌ",      # خنجريّة بلا حركةِ آخِر
 "A10_ملتصقة":         "هُوَاللّٰهُ أَحَدٌ",       # بلا مسافة قبلها
 "A11_لام_ألف_ممدودة": "هُوَ اللَّاهُ أَحَدٌ",    # شدّة+ألف صريحة
 "A12_قطع_خنجرية":     "هُوَ اَللّٰهُ أَحَدٌ",     # همزة قطع + خنجريّة
 "A13_عبارة_قال":      "قَالَ اللّٰهُ تَعَالَىٰ",  # سياقٌ آخَر (قال) بالخنجريّة
 "A14_عبارة_والله":    "وَاللّٰهُ أَكْبَرُ",       # والله بالخنجريّة
 "A15_نقطة_وقف":       "هُوَ الله. أَحَدٌ",        # نقطةٌ تفرضُ صيغةَ الوقف
}
voice=tts_engine.default_voice(); print("voice:",voice)
for name,txt in CASES.items():
    try:
        p,eng=tts_engine.synthesize(txt, voice=voice, rate_pct=0, word_gap=0, use_cache=False)
        dst=os.path.join(OUT, name+os.path.splitext(p)[1]); shutil.copy(p,dst)
        print(f"  OK {name}: {txt}")
    except Exception as e:
        print(f"  ERR {name}: {e}")
print("\nListen in recordings/jalalah_test2 and tell me which code is correct (A6..A15).")
