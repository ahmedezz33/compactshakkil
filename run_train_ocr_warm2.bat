@echo off
chcp 65001 >nul
cd /d %~dp0
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
echo [1/3] warm-start TRUE: v1 -> v4
set OCR_FRESH=1
set OCR_INIT_LORA=outputs_ocr_unified_v1
set OCR_LORA=outputs_ocr_bal_v4
set OCR_LR=3e-5
set OCR_EPOCHS=1
set OCR_MAXSIDE=896
set OCR_SAVE_EVERY=50
python train_ocr_qlora.py train --manifest data\ocr_unified_balanced.tsv --root .
if errorlevel 1 ( echo [ERROR] train & pause & exit /b 1 )
echo [2/3] eval v1 vs v4 (production gen params)
set OCR_FRESH=0
set OCR_INIT_LORA=
set OCR_PREPROCESS=0
set OCR_MAX_SIDE=1600
set OCR_REP_PENALTY=1.1
set OCR_NO_REPEAT=0
set OCR_MAX_TOKENS=4096
set OCR_LIMIT=0
set OCR_LORA=outputs_ocr_unified_v1
python diag_ocr_full.py > logs\eval_v1.log 2>&1
set OCR_LORA=outputs_ocr_bal_v4
python diag_ocr_full.py > logs\eval_v4.log 2>&1
echo DONE > logs\train_warm2_done.txt
echo [3/3] DONE. Adopt v4 ONLY if its median beats v1 on BOTH domains.
pause
