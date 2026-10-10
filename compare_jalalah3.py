# -*- coding: utf-8 -*-
"""compare_jalalah3.py — ضبطُ طول المدّ في صيغة A11 (اللَّاهُ) للتفخيم.
recordings/jalalah_test3/."""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")
OUT=os.path.join("recordings","jalalah_test3"); os.makedirs(OUT,exist_ok=True)

CASES={
 "C1_ألف_واحدة":     "هُوَ اللَّاهُ أَحَدٌ",       # A11 كما هي (مدٌّ قصير)
 "C2_ألفان":         "هُوَ اللَّااهُ أَحَدٌ",      # ألفان (مدٌّ أطول)
 "C3_مدة_آ":         "هُوَ اللَّآهُ أَحَدٌ",       # مدّة (آ)
 "C4_ألف+خنجرية":    "هُوَ اللَّاٰهُ أَحَدٌ",      # ألف + خنجريّة
 "C5_ثلاث_ألفات":    "هُوَ اللَّاااهُ أَحَدٌ",     # ثلاثُ ألفات (مدٌّ طويل)
 "C6_ألفان_خنجرية":  "هُوَ اللَّاٰاهُ أَحَدٌ",
 # نفسُ الأفضل مع عبارتين للتأكّد
 "C2b_قال":          "قَالَ اللَّااهُ تَعَالَىٰ",
 "C2c_والله":        "وَاللَّااهُ أَكْبَرُ",
}
voice=tts_engine.default_voice(); print("voice:",voice)
for name,txt in CASES.items():
    try:
        p,eng=tts_engine.synthesize(txt, voice=voice, rate_pct=0, word_gap=0, use_cache=False)
        shutil.copy(p, os.path.join(OUT, name+os.path.splitext(p)[1]))
        print(f"  OK {name}: {txt}")
    except Exception as e:
        print(f"  ERR {name}: {e}")
print("\nListen in recordings/jalalah_test3 and pick the best madd length (C1..C6).")
