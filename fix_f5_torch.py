# -*- coding: utf-8 -*-
"""
fix_f5_torch.py — يصلح تعارضَ torch/torchaudio بعد تثبيت f5-tts.

عند تثبيت f5-tts رُفِع torchaudio (و torchcodec) لنسخةٍ لا تطابق torch 2.5.1+cu121،
فظهر خطأ «torch_library_impl ... _torchaudio.pyd». نعيد torchaudio مطابقًا لـ torch،
ونزيل torchcodec المتعارض (f5 يقرأ الصوتَ عبر torchaudio/soundfile).
    python fix_f5_torch.py
"""
import sys, subprocess
def pip(*a): subprocess.run([sys.executable,"-m","pip",*a], check=False)

CU="https://download.pytorch.org/whl/cu121"
print("① إزالة torchaudio/torchcodec المتعارضَين …")
pip("uninstall","-y","torchaudio","torchcodec")
print("\n② تثبيت torchaudio مطابقًا لـ torch 2.5.1+cu121 …")
pip("install","torchaudio==2.5.1+cu121","--index-url",CU)
print("\n③ التحقّق …")
r=subprocess.run([sys.executable,"-c",
  "import torch,torchaudio;print('torch',torch.__version__,'cuda',torch.cuda.is_available());"
  "print('torchaudio',torchaudio.__version__)"], capture_output=True, text=True)
print(r.stdout or r.stderr)
if "cuda True" in (r.stdout or "").replace("cuda= ","cuda ") or "cuda True" in (r.stdout or ""):
    print("✅ تمّ الإصلاح. أعِد تشغيل التطبيق وجرّب زرَّ F5.")
else:
    print("راجِع المخرجات أعلاه. إن بقي التعارضُ أخبِرني به.")
