chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python -m pip install -q peft bitsandbytes accelerate --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_RESUME=1
set OCR_EPOCHS=1
set OCR_MAXSIDE=896
set OCR_LIMIT=0
echo === متابعة التدريب على صفحات كاملة + قصيرة (من محوّل القرآن) ===
python train_ocr_qlora.py train --manifest data\ocr_quran_combined.tsv --root .
echo === تقييم: اختبار الصفحات المحجوب ===
set OCR_LIMIT=0
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test_root.tsv --root .
echo === تقييم: اختبار الايات القصيرة (عدم تراجع) ===
set OCR_LIMIT=200
python train_ocr_qlora.py eval --manifest data\ocr_quran_test\manifest.tsv --root data\ocr_quran_test
pause
