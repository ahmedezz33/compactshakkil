# -*- coding: utf-8 -*-
"""
download_piper_voice.py — يُنزّل نموذجَ صوتٍ عربيٍّ لـ Piper إلى voices/.

Piper محرّكٌ عصبيٌّ يعمل محلّيًّا (بلا إنترنت بعد التنزيل)، وتشكيلُه أمينٌ عبر
قواعد espeak — فلا يُخطئ السكونَ/الشدّةَ كما يفعل edge. النموذجُ الافتراضيّ:
ar_JO-kareem-medium (فصحى، ٦٣ م.ب). يعمل على جهازك (يحتاج إنترنت مرّةً للتنزيل).

    python download_piper_voice.py
"""
import os, sys, urllib.request

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium/"
FILES = ["ar_JO-kareem-medium.onnx", "ar_JO-kareem-medium.onnx.json"]
DST = "voices"

def main():
    os.makedirs(DST, exist_ok=True)
    for fn in FILES:
        dst = os.path.join(DST, fn)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            print(f"✔ موجودٌ سلفًا: {fn}"); continue
        url = BASE + fn
        print(f"⏳ تنزيل {fn} …"); sys.stdout.flush()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
                total = int(r.headers.get("Content-Length", 0)); got = 0
                while True:
                    chunk = r.read(65536)
                    if not chunk: break
                    f.write(chunk); got += len(chunk)
                    if total:
                        print(f"\r   {got*100//total}%  ({got//1024} ك.ب)", end=""); sys.stdout.flush()
            print(f"\r✅ اكتمل: {fn}            ")
        except Exception as e:
            print(f"\n❌ إخفاق {fn}: {e}")
            try:
                if os.path.exists(dst): os.remove(dst)
            except Exception: pass
            print("أعِد المحاولة، أو نزّل الملفّ يدويًّا من:", url)
            return
    print("\n✅ النموذجُ جاهزٌ في voices/.")
    print("ثبِّت محرّكَ Piper مرّةً:  pip install piper-tts")
    print("ثمّ أعِد تشغيلَ التطبيق واختر «Piper محلّيّ» أو زرَّ «انطق (Piper)».")

if __name__ == "__main__":
    main()
