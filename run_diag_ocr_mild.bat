@echo off
chcp 65001 >nul
cd /d %~dp0
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_PREPROCESS=0
set OCR_MAX_SIDE=1600
set OCR_REP_PENALTY=1.1
set OCR_NO_REPEAT=0
set OCR_MAX_TOKENS=4096
if "%1"=="" (set OCR_LORA=outputs_ocr_unified_v1) else (set OCR_LORA=%1)
if "%2"=="" (set OCR_LIMIT=0) else (set OCR_LIMIT=%2)
echo === LoRA=%OCR_LORA% REP=%OCR_REP_PENALTY% NOREP=%OCR_NO_REPEAT% MAXTOK=%OCR_MAX_TOKENS% ===
python diag_ocr_full.py
pause
