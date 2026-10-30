@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_EVAL_MAXTOK=2048
echo === قراءة مبكرة: المحول نصف المدرب (bal_v2) مقابل الاساس و v1 ===
python strip_waqf_manifest.py data\ocr_quran_pages_test\manifest.tsv data\ocr_quran_pages_test\manifest_clean.tsv

echo [القران] اساس / v1 / v2(نصف) ...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_NOLORA=0
set OCR_LORA=outputs_ocr_unified_v1
if exist outputs_ocr_unified_v1\adapter_config.json python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_LORA=outputs_ocr_bal_v2
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test

echo [التراث] اساس / v1 / v2(نصف) ...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_NOLORA=0
set OCR_LORA=outputs_ocr_unified_v1
if exist outputs_ocr_unified_v1\adapter_config.json python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_LORA=outputs_ocr_bal_v2
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test

echo تم. هذه قراءة مبكرة (نصف تدريب) — اشارة لا حكم نهائي.
pause
