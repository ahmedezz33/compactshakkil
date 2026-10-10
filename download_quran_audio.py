# -*- coding: utf-8 -*-
"""
download_quran_audio.py — يسحب تلاوةَ القرآن (آية-آية) إلى recordings/quran/.

المصدر: everyayah.com (ملفّاتٌ باسم SSSAAA.mp3 لكلّ قارئ). يتخطّى الموجودَ،
فيمكن إيقافُه واستئنافُه. يعمل على جهازك (يحتاج إنترنت).

    python download_quran_audio.py                         # القارئ الافتراضيّ (العفاسي)
    python download_quran_audio.py --reciter Husary_128kbps
    python download_quran_audio.py --sura 2                 # سورةٌ واحدةٌ فقط
"""
import os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quran_audio as qa

RECITER = "Alafasy_128kbps"
BASE = "https://everyayah.com/data/{r}/{c}.mp3"

def main():
    a = sys.argv[1:]
    global RECITER
    if "--reciter" in a:
        try: RECITER = a[a.index("--reciter")+1]
        except Exception: pass
    only_sura = None
    if "--sura" in a:
        try: only_sura = int(a[a.index("--sura")+1])
        except Exception: pass

    codes = qa.all_codes()
    if only_sura:
        codes = [c for c in codes if int(c[:3]) == only_sura]
    os.makedirs(qa.QDIR, exist_ok=True)
    tot = len(codes); done = got = have = fail = 0
    print(f"⏳ تنزيل التلاوة — القارئ: {RECITER} | الآيات: {tot}")
    for c in codes:
        done += 1
        dst = os.path.join(qa.QDIR, c + ".mp3")
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            have += 1
            if done % 100 == 0: print(f"   … {done}/{tot}"); sys.stdout.flush()
            continue
        url = BASE.format(r=RECITER, c=c)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            if not data: raise RuntimeError("empty")
            with open(dst, "wb") as f: f.write(data)
            got += 1
        except Exception as e:
            fail += 1
            try:
                if os.path.exists(dst): os.remove(dst)
            except Exception: pass
            if fail <= 5: print(f"   إخفاق {c}: {e}")
        if done % 50 == 0:
            print(f"   … {done}/{tot} (نُزِّل {got}, موجود {have}, إخفاق {fail})"); sys.stdout.flush()
    print(f"✅ اكتمل: نُزِّل {got}, موجودٌ سلفًا {have}, إخفاق {fail}, المجموع {tot}")
    if fail:
        print("أعِد تشغيلَ الأمر لإكمال ما أخفق (يتخطّى المُنزَّل).")
    print("أعِد تشغيلَ التطبيق — ستُنطَق الآياتُ بالتلاوة الحقيقيّة.")

if __name__ == "__main__":
    main()
