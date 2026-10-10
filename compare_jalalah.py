# -*- coding: utf-8 -*-
"""compare_jalalah.py — يولّدُ «هو الله أحد» بصيغٍ نصّيّةٍ مختلفةٍ لِلفظ الجلالة
بمحرّك edge، لتستمعَ وتختارَ الأصحَّ نطقًا. الملفّاتُ في recordings/jalalah_test/."""
import os, sys, shutil, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")
OUT=os.path.join("recordings","jalalah_test"); os.makedirs(OUT,exist_ok=True)

# نختبرُ عبارتين: بعد فتح (تفخيم) وبعد كسر (ترقيق)
CASES={
 # هُوَ (فتح) → المفروض تفخيم
 "A1_تفخيم_مجرد":      "هُوَ الله أَحَدٌ",
 "A2_تفخيم_شدة":       "هُوَ اللَّه أَحَدٌ",
 "A3_تفخيم_كامل":      "هُوَ اللَّهُ أَحَدٌ",
 "A4_تفخيم_سكون":      "هُوَ اللَّهْ أَحَدٌ",
 "A5_تفخيم_فاصلة":     "هُوَ، الله أَحَدٌ",
 # بِسمِ (كسر) → المفروض ترقيق
 "B1_ترقيق_مجرد":      "بِسْمِ الله",
 "B2_ترقيق_شدة":       "بِسْمِ اللَّه",
 "B3_ترقيق_كامل":      "بِسْمِ اللَّهِ",
}
voice=tts_engine.default_voice(); print("voice:",voice)
for name,txt in CASES.items():
    try:
        p,eng=tts_engine.synthesize(txt, voice=voice, rate_pct=-10, word_gap=0, use_cache=False)
        dst=os.path.join(OUT, name+os.path.splitext(p)[1])
        shutil.copy(p, dst)
        print(f"  ✅ {name}: {txt}  -> {dst}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
print("\nاستمعْ للملفّات في",OUT,"وأخبرْني: أيُّ رمزٍ (A1..A5 / B1..B3) نطقُه أصحّ؟")
