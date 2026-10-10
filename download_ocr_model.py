# -*- coding: utf-8 -*-
"""ينزّلُ نموذجَ OCR المحدّدَ في ocr_model.txt (أو وسيطٍ) إلى مخزنِ HuggingFace. بلا GPU."""
import sys, os
mid = sys.argv[1] if len(sys.argv) > 1 else None
if not mid and os.path.exists("ocr_model.txt"):
    mid = open("ocr_model.txt", encoding="utf-8").read().strip()
if not mid:
    print("لا نموذج محدّد"); sys.exit(1)
print("تنزيل:", mid)
from huggingface_hub import snapshot_download
snapshot_download(mid)
print("تمّ تنزيل:", mid)
