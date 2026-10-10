chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_RESUME=1
set OCR_EPOCHS=1
set OCR_LIMIT=0
echo === متابعة التدريب من المحوّلات المحفوظة (حقبة اضافية) ===
python train_ocr_qlora.py train --manifest data\ocr_quran\manifest.tsv --root data\ocr_quran
echo === تقييم بعد المتابعة ===
set OCR_LIMIT=200
python train_ocr_qlora.py eval --manifest data\ocr_quran_test\manifest.tsv --root data\ocr_quran_test
pause
