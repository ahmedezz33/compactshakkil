# -*- coding: utf-8 -*-
"""
setup_f5.py — إعدادُ Arabic F5-TTS مرّةً واحدة (على جهازك ذي الـ GPU).

يثبّت مكتبةَ f5-tts و huggingface_hub، ثمّ ينزّل أوزانَ النموذج (~عدّة مئات م.ب)
إلى models/arabic_f5/. بعده اختر «F5 العربيّ» في التطبيق أو زرَّ «انطق (F5)».

    python setup_f5.py
"""
import sys, subprocess

def pip(*args):
    subprocess.run([sys.executable, "-m", "pip", "install", *args], check=True)

def main():
    print("① تثبيت f5-tts و huggingface_hub …")
    try:
        pip("f5-tts", "huggingface_hub")
    except Exception as e:
        print("⚠️ تعذّر التثبيت التلقائيّ:", e)
        print("ثبّت يدويًّا:  pip install f5-tts huggingface_hub")
        return
    print("\n② التحقّق من GPU …")
    try:
        import torch
        print("   torch", torch.__version__, "| CUDA:", torch.cuda.is_available(),
              "|", (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "بلا GPU"))
        if not torch.cuda.is_available():
            print("   ⚠️ لا GPU مرئيّ — سيعمل على المعالج (بطيء). تأكّد من torch بنسخة CUDA.")
    except Exception as e:
        print("   ⚠️ torch غير متاح:", e)
    print("\n③ تنزيل أوزان النموذج …")
    import f5_engine
    f5_engine.ensure_model()
    print("\n✅ اكتمل الإعداد. أعِد تشغيل التطبيق واختر «F5 العربيّ».")
    print("   لأفضل صوتٍ ثابت: حرّر f5_reference.json (صوتٌ مرجعيّ + نصُّه المشكّل).")

if __name__ == "__main__":
    main()
