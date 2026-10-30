@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_PREPROCESS=0
set OCR_LIMIT=0
set SWEEP=res2
echo === تاكيد MAX_SIDE (1600 ضد 2600) على 61 صفحة ===
python eval_ocr_res2.py
pause
