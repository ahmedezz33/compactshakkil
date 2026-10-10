# -*- coding: utf-8 -*-
"""
make_hamed_reference.py — يصنع مرجعَ F5 بصوت حامد النظيف.

الفكرة: نولّد جملةً واضحةً بصوت حامد (edge، استوديو بلا ضوضاء)، نحوّلها wav،
ونضبط f5_reference.json عليها. فيستنسخ F5 نبرةَ حامد لكن بنطقٍ صحيحٍ للتشكيل.
يعمل على جهازك (يحتاج إنترنت لحامد، وffmpeg — مثبَّتٌ سلفًا).
    python make_hamed_reference.py
"""
import os, sys, json, asyncio, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VOICE   = "ar-SA-HamedNeural"
# جملةٌ مرجعيّةٌ واضحةٌ (٨–١٠ ثوانٍ) — النصُّ يُطابق الصوتَ تمامًا
REF_TEXT = ("أَهْلًا وَسَهْلًا، هَذَا صَوْتٌ عَرَبِيٌّ وَاضِحٌ وَنَقِيٌّ، "
            "نَقْرَأُ بِهِ النُّصُوصَ قِرَاءَةً سَلِيمَةً جَمِيلَةً.")
MP3 = os.path.join("voices","_hamed_ref.mp3")
WAV = os.path.join("voices","f5_ref_hamed.wav")

def main():
    os.makedirs("voices", exist_ok=True)
    print("① توليد مقطع حامد المرجعيّ (edge) …"); sys.stdout.flush()
    import edge_tts
    asyncio.run(edge_tts.Communicate(REF_TEXT, VOICE).save(MP3))
    if not os.path.exists(MP3) or os.path.getsize(MP3)==0:
        print("❌ فشل توليدُ صوت حامد (إنترنت؟)"); return
    print("② تحويل إلى WAV أحاديّ ٢٤ك …"); sys.stdout.flush()
    ff = shutil.which("ffmpeg") or "ffmpeg"
    r = subprocess.run([ff,"-y","-i",MP3,"-ac","1","-ar","24000",WAV],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode!=0 or not os.path.exists(WAV):
        print("❌ فشل ffmpeg:\n", r.stderr[-400:]); return
    json.dump({"ref_audio":WAV.replace("\\","/"), "ref_text":REF_TEXT},
              open("f5_reference.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ تمّ. مرجعُ F5 الآن صوتُ حامد النظيف: {WAV}")
    print("جرّب زرَّ F5 في التطبيق (لا يحتاج إعادةَ تشغيل).")

if __name__ == "__main__":
    main()
