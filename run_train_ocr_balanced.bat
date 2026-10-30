@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
python -m pip install -q peft bitsandbytes accelerate --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt

echo ============================================================
echo  OCR متوازن: تدريب v2 جديد + مقارنة (اساس / v1 / v2) قران+تراث
echo ============================================================

if "%QREP%"=="" set QREP=2
echo [1/5] بناء المانيفست المتوازن (قران×%QREP% + تراث)...
python build_balanced_tsv.py
if errorlevel 1 ( echo [khata] balanced tsv & pause & exit /b 1 )

echo [2/5] تدريب محول متوازن جديد (outputs_ocr_bal_v2)...
set OCR_LORA=outputs_ocr_bal_v2
set OCR_MAXSIDE=896
if "%OCR_EPOCHS%"=="" set OCR_EPOCHS=2
set OCR_SAVE_EVERY=50
python train_ocr_qlora.py train --manifest data\ocr_unified_balanced.tsv --root .
if errorlevel 1 ( echo [khata] train & pause & exit /b 1 )

set OCR_EVAL_MAXTOK=2048
python strip_waqf_manifest.py data\ocr_quran_pages_test\manifest.tsv data\ocr_quran_pages_test\manifest_clean.tsv

echo [3/5] تقييم القران: اساس / v1 / v2 ...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_NOLORA=0
set OCR_LORA=outputs_ocr_unified_v1
if exist outputs_ocr_unified_v1\adapter_config.json python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_LORA=outputs_ocr_bal_v2
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test

echo [4/5] تقييم التراث: اساس / v1 / v2 ...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_NOLORA=0
set OCR_LORA=outputs_ocr_unified_v1
if exist outputs_ocr_unified_v1\adapter_config.json python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_LORA=outputs_ocr_bal_v2
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test

echo [5/5] تم. اعتمد v2 فقط لو قل CER على القران *و* التراث مقابل v1 والاساس.
echo النموذج الجيد الحالي (outputs_ocr_unified / _v1) لم يمس.
pause
