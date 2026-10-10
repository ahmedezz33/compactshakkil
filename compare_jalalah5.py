# -*- coding: utf-8 -*-
"""compare_jalalah5.py — C1 مع إدراج حرف A/a اللاتينيّ لصوت المدّ. recordings/jalalah_test5/"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")
OUT=os.path.join("recordings","jalalah_test5"); os.makedirs(OUT,exist_ok=True)
CASES={
 "E1_مرجع_C1":       "هُوَ اللَّاهُ أَحَدٌ",
 "E2_A_بعد_الشدة":   "هُوَ اللَّAهُ أَحَدٌ",       # A مكان المدّ
 "E3_a_صغيرة":       "هُوَ اللَّaهُ أَحَدٌ",
 "E4_A_بعد_ألف":     "هُوَ اللَّاAهُ أَحَدٌ",
 "E5_A_بمسافة":      "هُوَ الله A هُ أَحَدٌ",
 "E6_لام_A_مباشرة":  "هُوَ اللAهُ أَحَدٌ",
 "E7_Aa":            "هُوَ اللَّAaهُ أَحَدٌ",
}
voice=tts_engine.default_voice(); print("voice:",voice)
for name,txt in CASES.items():
    try:
        p,eng=tts_engine.synthesize(txt, voice=voice, rate_pct=0, word_gap=0, use_cache=False)
        shutil.copy(p, os.path.join(OUT, name+os.path.splitext(p)[1]))
        print(f"  OK {name}: {txt}")
    except Exception as e:
        print(f"  ERR {name}: {e}")
print("\nListen in recordings/jalalah_test5 and pick the best (E1..E7).")
