@echo off
chcp 65001 >nul
cd /d "%~dp0"

call venv\Scripts\activate.bat
if errorlevel 1 ( echo [خطأ] تعذّر تفعيل venv & pause & exit /b 1 )
python -m pip install -q peft bitsandbytes accelerate --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt

echo ============================================================
echo  OCR موحّد (الصور مُصيّرة مسبقًا على الجسر) — تدريب + تقييم
echo ============================================================

echo [1/4] بناء المانيفست الموحّد (قرآن + تراث)...
python build_unified_tsv.py
if errorlevel 1 ( echo [خطأ] فشل بناء المانيفست & pause & exit /b 1 )

echo [2/4] تدريب محوّل موحّد جديد (outputs_ocr_unified)...
set OCR_LORA=outputs_ocr_unified
set OCR_MAXSIDE=896
set OCR_EPOCHS=2
set OCR_SAVE_EVERY=50
REM نسخة احتياطية للنموذج الجيّد الحاليّ (مرّة واحدة) قبل إعادة التدريب
if exist outputs_ocr_unified\adapter_config.json if not exist outputs_ocr_unified_v1\adapter_config.json (
  echo [نسخ احتياطيّ] outputs_ocr_unified ← outputs_ocr_unified_v1
  xcopy /E /I /Y outputs_ocr_unified outputs_ocr_unified_v1 >nul
)
python train_ocr_qlora.py train --manifest data\ocr_unified_train.tsv --root .
if errorlevel 1 ( echo [خطأ] فشل التدريب & pause & exit /b 1 )

set OCR_EVAL_MAXTOK=1024
echo [3/4] تقييم القرآن (ذهبيّ نظيف؛ الصور بالرموز)...
python strip_waqf_manifest.py data\ocr_quran_pages_test\manifest.tsv data\ocr_quran_pages_test\manifest_clean.tsv
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test
set OCR_NOLORA=0
python train_ocr_qlora.py eval --manifest data\ocr_quran_pages_test\manifest_clean.tsv --root data\ocr_quran_pages_test

echo [4/4] تقييم التراث (أساس ثم موحّد)...
set OCR_NOLORA=1
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test
set OCR_NOLORA=0
python train_ocr_qlora.py eval --manifest data\ocr_classical_pages_test\manifest.tsv --root data\ocr_classical_pages_test

echo.
echo تمّ. قارِن CER: الأساس مقابل الموحّد على القرآن والتراث (سقف 1024).
pause
