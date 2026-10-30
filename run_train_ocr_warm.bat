@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
python -m pip install -q peft bitsandbytes accelerate --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt

echo ============================================================
echo  تدريب دافئ: ننطلق من v1 (يتقن القران) ونحسن التراث — حقبة واحدة
echo ============================================================
if "%QREP%"=="" set QREP=2
echo [1/4] بناء المانيفست المتوازن (قران×%QREP%)...
python build_balanced_tsv.py
if errorlevel 1 ( echo [khata] balanced tsv & pause & exit /b 1 )

echo [2/4] تدريب دافئ على outputs_ocr_bal_v3 (انطلاق من v1)...
set OCR_LORA=outputs_ocr_bal_v3
set OCR_MAXSIDE=896
set OCR_EPOCHS=1
set OCR_SAVE_EVERY=50
python train_ocr_qlora.py train --manifest data\ocr_unified_balanced.tsv --root .
if errorlevel 1 ( echo [khata] train & pause & exit /b 1 )

set OCR_EVAL_MAXTOK=2048
python strip_waqf_manifest.py data\ocr_quran_pages_test\manifest.tsv data\ocr_quran_pages_test\manifest_clean.tsv
echo [3/4] تقييم القران: اساس / v1 / v3 ...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_NOLORA=0
set OCR_LORA=outputs_ocr_unified_v1
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_LORA=outputs_ocr_bal_v3
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test

echo [4/4] تقييم التراث: اساس / v1 / v3 ...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_NOLORA=0
set OCR_LORA=outputs_ocr_unified_v1
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_LORA=outputs_ocr_bal_v3
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test

echo تم. اعتمد v3 فقط لو قل CER على القران *و* التراث مقابل v1. المنشور لم يمس.
pause
