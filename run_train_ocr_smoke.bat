chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python -m pip install -q peft bitsandbytes accelerate --disable-pip-version-check
echo === تجربة سريعة: 300 صورة فقط (فحص الذاكرة) ===
set OCR_LIMIT=300
set OCR_EPOCHS=1
python train_ocr_qlora.py train --manifest data\ocr_quran\manifest.tsv --root data\ocr_quran
echo === تقييم سريع بعد التجربة ===
set OCR_LIMIT=100
python train_ocr_qlora.py eval --manifest data\ocr_quran_test\manifest.tsv --root data\ocr_quran_test
pause
