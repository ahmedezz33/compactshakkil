# -*- coding: utf-8 -*-
"""
compare_voices.py — يولّد جملةَ اختبارٍ واحدةً بكلّ أصوات edge العربيّة لتختار الأصحَّ.

يعمل على جهازك (edge-tts + إنترنت). يحفظ ملفًّا لكلّ صوتٍ في voices_test/،
مسمّى برقمٍ + معرّف الصوت، فتشغّلها بالترتيب وتسمع أيُّها ينطق:
  • السكون سكونًا (قُلْتُمْ لا قُلُتُم)      • الشدّة مرّةً لا زائدة (فَرَقْنَا لا فرّقنا)
  • اللام الشمسيّة/القمريّة صحيحةً          • المدَّ طويلًا (تَنظُرُونَ)

    python compare_voices.py                 # الجملة الافتراضيّة، كلُّ الأصوات
    python compare_voices.py "نصُّك المشكّل"   # جملةُ اختبارٍ من عندك
"""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pronounce import edge_prepare

# جملةُ اختبارٍ تجمع: سكون + لام قمريّة + لام شمسيّة مشدّدة + تشديد سياقيّ + مدّ
TEST = ("قُلْتُمْ الْحَمْدُ لِلَّهِ التَّوَّابُ الرَّحِيمُ "
        "وَإِذْ فَرَقْنَا بِكُمُ الْبَحْرَ أَفَلَا تَنظُرُونَ")

# أصواتُ edge العربيّة (ذكرٌ/أنثى لكلّ لهجة) — مرتَّبةٌ بالأولى للتجربة أعلى
VOICES = [
    # الأرجحُ وضوحًا في التشكيل (فصحى إخباريّة) — جرّبها أوّلًا
    "ar-EG-ShakerNeural", "ar-SA-HamedNeural", "ar-SA-ZariyahNeural",
    "ar-EG-SalmaNeural", "ar-AE-HamdanNeural", "ar-JO-TaimNeural",
    "ar-BH-AliNeural", "ar-QA-MoazNeural", "ar-KW-FahedNeural",
    "ar-SY-LaithNeural", "ar-IQ-BasselNeural", "ar-OM-AbdullahNeural",
    # البقيّة
    "ar-AE-FatimaNeural", "ar-BH-LailaNeural", "ar-DZ-AminaNeural",
    "ar-DZ-IsmaelNeural", "ar-IQ-RanaNeural", "ar-JO-SanaNeural",
    "ar-KW-NouraNeural", "ar-LB-LaylaNeural", "ar-LB-RamiNeural",
    "ar-LY-ImanNeural", "ar-LY-OmarNeural", "ar-MA-JamalNeural",
    "ar-MA-MounaNeural", "ar-OM-AyshaNeural", "ar-QA-AmalNeural",
    "ar-SY-AmanyNeural", "ar-TN-HediNeural", "ar-TN-ReemNeural",
    "ar-YE-MaryamNeural", "ar-YE-SalehNeural",
]

def main():
    text = sys.argv[1] if len(sys.argv) > 1 else TEST
    spoken = edge_prepare(text, mode="waqf")
    out = "voices_test"; os.makedirs(out, exist_ok=True)
    print("النصُّ المُغذَّى:", spoken)
    print(f"توليدُ {len(VOICES)} صوتًا في «{out}/» …\n")
    import edge_tts
    ok = fail = 0
    for i, v in enumerate(VOICES, 1):
        dst = os.path.join(out, f"{i:02d}_{v}.mp3")
        try:
            async def go():
                await edge_tts.Communicate(spoken, v).save(dst)
            asyncio.run(go())
            ok += 1; print(f"  ✅ {i:02d}  {v}")
        except Exception as e:
            fail += 1; print(f"  ❌ {i:02d}  {v}: {e}")
    print(f"\nاكتمل: {ok} نجح، {fail} أخفق.")
    print(f"افتح مجلّد «{out}» وشغّل الملفّات بالترتيب. اسمع الأصحَّ في السكون")
    print("والتشديد واللام، وأخبِرني برقمه/اسمه لأجعله الصوتَ الافتراضيَّ للتطبيق.")

if __name__ == "__main__":
    main()
