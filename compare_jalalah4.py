# -*- coding: utf-8 -*-
"""compare_jalalah4.py — C1 + فتحة/مدّ صغير على اللام الأولى (تفخيم). recordings/jalalah_test4/"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")
OUT=os.path.join("recordings","jalalah_test4"); os.makedirs(OUT,exist_ok=True)
CASES={
 "D1_C1_أساس":        "هُوَ اللَّاهُ أَحَدٌ",     # C1 كما هي (مرجع)
 "D2_فتحة_أولى":       "هُوَ الَّاهُ أَحَدٌ",      # فتحة+شدّة على اللام الأولى + ألف
 "D3_خنجرية_بعد_الشدة":"هُوَ اللَّٰاهُ أَحَدٌ",    # ألف خنجريّة (مدٌّ صغير) بعد اللام المشدّدة
 "D4_فتحة_ألف":        "هُوَ الَاهُ أَحَدٌ",       # لام واحدة بفتحة + ألف
 "D5_قطع_فتحة":        "هُوَ اَللَّاهُ أَحَدٌ",    # همزة قطع بفتحة على الألف
 "D6_صريح":            "هُوَ اَلْلَاهُ أَحَدٌ",    # لام أولى ساكنة + ثانية بفتحة+ألف
 "D7_خنجرية_فقط":      "هُوَ اللَّٰهُ أَحَدٌ",     # خنجريّة بلا ألف صريحة (مدّ صغير)
}
voice=tts_engine.default_voice(); print("voice:",voice)
for name,txt in CASES.items():
    try:
        p,eng=tts_engine.synthesize(txt, voice=voice, rate_pct=0, word_gap=0, use_cache=False)
        shutil.copy(p, os.path.join(OUT, name+os.path.splitext(p)[1]))
        print(f"  OK {name}: {txt}")
    except Exception as e:
        print(f"  ERR {name}: {e}")
print("\nListen in recordings/jalalah_test4 and pick the best (D1..D7).")
