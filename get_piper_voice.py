# -*- coding: utf-8 -*-
"""
get_piper_voice.py — ينزّل صوتَ Piper العربيّ (ar_JO-kareem-medium) إلى مجلّد voices/.
محلّيٌّ بالكامل بعد التنزيل (بلا إنترنت لاحقًا). التشغيل: python get_piper_voice.py
"""
import os, sys, urllib.request
BASE=("https://huggingface.co/rhasspy/piper-voices/resolve/main/"
      "ar/ar_JO/kareem/medium/")
FILES=["ar_JO-kareem-medium.onnx","ar_JO-kareem-medium.onnx.json"]
OUT="voices"

def hook(b,bs,total):
    if total>0:
        pct=min(100,100*b*bs/total)
        sys.stdout.write(f"\r   {pct:5.1f}%"); sys.stdout.flush()

def main():
    os.makedirs(OUT,exist_ok=True)
    for f in FILES:
        dst=os.path.join(OUT,f)
        if os.path.exists(dst) and os.path.getsize(dst)>0:
            print(f"✅ موجود: {f}"); continue
        print(f"⤵️  تنزيل: {f}")
        try:
            urllib.request.urlretrieve(BASE+f, dst, hook); print("  ✔")
        except Exception as e:
            print(f"\n❌ فشل تنزيل {f}: {e}\n   حمّله يدويًّا من:\n   {BASE+f}\n   وضعه في مجلّد {OUT}/")
            return
    print(f"\n🎉 تمّ. الصوت جاهزٌ في {OUT}/ — أعِد تشغيل التطبيق واختر «★ Piper محلّيّ».")

if __name__=="__main__": main()
