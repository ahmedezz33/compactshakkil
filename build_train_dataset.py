# -*- coding: utf-8 -*-
"""
build_train_dataset.py — يجهّز بياناتِ صقلِ F5 من تلاوة المنشاوي المرتّل (القرآن كاملًا).

المخرجات في train_data/minshawy/ :
  wavs/SSSAAA.wav     صوتٌ أحاديٌّ ٢٤ك (صيغةُ F5)
  metadata.csv        أسطر: wavs/SSSAAA.wav|<نصُّ الآية مشكّلًا>
المصدر: everyayah.com/data/Minshawy_Murattal_128kbps (آية-آية). قابلٌ للاستئناف.
يعمل على جهازك (إنترنت + ffmpeg — مثبَّتٌ سلفًا).

    python build_train_dataset.py                 # تنزيل + تحويل + بناء metadata
    python build_train_dataset.py --skip-download  # تحويلٌ وبناءٌ فقط
    python build_train_dataset.py --limit 100      # تجربةٌ سريعةٌ (أوّل ١٠٠ آية)
"""
import os, sys, re, subprocess, shutil, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quran_audio as qa
from pronounce import normalize_marks

RECITER = "Minshawy_Murattal_128kbps"
BASE    = "https://everyayah.com/data/{r}/{c}.mp3"
ROOT    = os.path.join("train_data", "minshawy")
MP3D    = os.path.join(ROOT, "mp3")
WAVD    = os.path.join(ROOT, "wavs")
META    = os.path.join(ROOT, "metadata.csv")
QTXT    = "data/raw/quran/quran-simple.txt"
SR      = 24000                                   # F5 يعمل على ٢٤ك

# احتفظ بالحروف والحركات (والخنجريّة والوصل) فقط — نصٌّ نظيفٌ للتدريب
_KEEP = re.compile(r"[^ء-ْٰٱ ]")
def clean(t):
    t = normalize_marks(t)
    return " ".join(_KEEP.sub(" ", t).split())

def ayah_texts():
    """قائمةٌ مرتّبةٌ [(code, text)] لكلّ آية (٦٢٣٦) بترتيب حفص المطابق للمصدر."""
    lines = qa._lines(QTXT)
    codes = qa.all_codes()
    if len(lines) != len(codes):
        raise SystemExit(f"❌ عدد أسطر النصّ {len(lines)} ≠ عدد الآيات {len(codes)} — تحقّق من {QTXT}")
    return list(zip(codes, lines))

def ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"

def main():
    a = sys.argv[1:]
    skip_dl = "--skip-download" in a
    limit = None
    if "--limit" in a:
        try: limit = int(a[a.index("--limit")+1])
        except Exception: pass

    pairs = ayah_texts()
    if limit: pairs = pairs[:limit]
    os.makedirs(MP3D, exist_ok=True); os.makedirs(WAVD, exist_ok=True)
    ff = ffmpeg()
    tot = len(pairs); dl = conv = have = fail = 0
    rows = []
    print(f"⏳ تجهيز {tot} آية — القارئ {RECITER}")
    for i, (code, raw) in enumerate(pairs, 1):
        mp3 = os.path.join(MP3D, code + ".mp3")
        wav = os.path.join(WAVD, code + ".wav")
        # (١) تنزيل
        if not skip_dl and not (os.path.exists(mp3) and os.path.getsize(mp3) > 0):
            try:
                req = urllib.request.Request(BASE.format(r=RECITER, c=code),
                                             headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as r, open(mp3, "wb") as f:
                    f.write(r.read())
                dl += 1
            except Exception as e:
                fail += 1
                if fail <= 5: print(f"   إخفاق تنزيل {code}: {e}")
                continue
        if not os.path.exists(mp3): continue
        # (٢) تحويل إلى wav ٢٤ك أحاديّ
        if not (os.path.exists(wav) and os.path.getsize(wav) > 0):
            r = subprocess.run([ff, "-y", "-i", mp3, "-ac", "1", "-ar", str(SR), wav],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0: conv += 1
            else:
                fail += 1
                if fail <= 5: print(f"   إخفاق تحويل {code}")
                continue
        else:
            have += 1
        # (٣) سطرُ metadata (F5 يطلب مسارًا مطلقًا)
        txt = clean(raw)
        if txt:
            rows.append(f"{os.path.abspath(wav)}|{txt}")
        if i % 100 == 0:
            print(f"   … {i}/{tot} (نُزّل {dl}, حُوّل {conv}, موجود {have}, إخفاق {fail})")
            sys.stdout.flush()
    # اكتب metadata بصيغة F5: ترويسة audio_file|text ثمّ الأسطر (UTF-8 بلا BOM)
    with open(META, "w", encoding="utf-8") as f:
        f.write("audio_file|text\n" + "\n".join(rows) + "\n")
    print(f"\n✅ اكتمل: {len(rows)} سطرًا في {META}")
    print(f"   wavs في {WAVD} | مجموع الإخفاق {fail}")
    if fail:
        print("   أعِد تشغيلَ الأمر لإكمال ما أخفق (يتخطّى المُنجَز).")
    print("التالي: مرحلةُ الصقل (سأعطيك سكربتَها بعد اكتمال البيانات).")

if __name__ == "__main__":
    main()
