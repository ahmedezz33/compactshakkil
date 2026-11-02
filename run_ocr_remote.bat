@echo off
chcp 65001 >nul
cd /d %~dp0
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_PREPROCESS=0
set OCR_MAX_SIDE=1600
set OCR_LORA=outputs_ocr_unified_v1
set OCR_LIMIT=0
echo [%date% %time%] START mild rep1.1
set OCR_REP_PENALTY=1.1& set OCR_NO_REPEAT=0& set OCR_MAX_TOKENS=4096
python diag_ocr_full.py > logs\diag_mild.log 2>&1
echo [%date% %time%] START plain rep1.0 cap2048
set OCR_REP_PENALTY=1.0& set OCR_NO_REPEAT=0& set OCR_MAX_TOKENS=2048
python diag_ocr_full.py > logs\diag_plain2048.log 2>&1
echo [%date% %time%] ALL DONE > logs\remote_done.txt
echo ============ DONE — logs in logs\ ============
