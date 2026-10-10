# -*- coding: utf-8 -*-
"""compare_jalalah6.py — C1 مع إدراج حرف H/h اللاتينيّ. recordings/jalalah_test6/"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")
OUT=os.path.join("recordings","jalalah_test6"); os.makedirs(OUT,exist_ok=True)
CASES={
 "F1_مرجع_C1":       "هُوَ اللَّاهُ أَحَدٌ",
 "F2_H_مكان_الهاء":  "هُوَ اللَّاH أَحَدٌ",
 "F3_h_صغيرة":       "هُوَ اللَّاh أَحَدٌ",
 "F4_H_بعد_الهاء":   "هُوَ اللَّاهH أَحَدٌ",
 "F5_H_بمسافة":      "هُوَ اللَّاه H أَحَدٌ",
 "F6_A_ثم_H":        "هُوَ اللَّAH أَحَدٌ",
 "F7_ah":            "هُوَ اللَّاah أَحَدٌ",
 "F8_Ah":            "هُوَ اللَّAh أَحَدٌ",
}
voice=tts_engine.default_voice(); print("voice:",voice)
for name,txt in CASES.items():
    try:
        p,eng=tts_engine.synthesize(txt, voice=voice, rate_pct=0, word_gap=0, use_cache=False)
        shutil.copy(p, os.path.join(OUT, name+os.path.splitext(p)[1]))
        print(f"  OK {name}: {txt}")
    except Exception as e:
        print(f"  ERR {name}: {e}")
print("\nListen in recordings/jalalah_test6 and pick the best (F1..F8).")
