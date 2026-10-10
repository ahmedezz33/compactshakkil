chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_LIMIT=200
echo === Qari الاساس (بدون LoRA) ===
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_quran_test\manifest.tsv --root data\ocr_quran_test
echo === Qari + LoRA (بعد تدريب القران) ===
set OCR_NOLORA=0
python train_ocr_qlora.py eval --manifest data\ocr_quran_test\manifest.tsv --root data\ocr_quran_test
pause
