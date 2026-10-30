@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set SWEEP=prompt
if "%1"=="" (set OCR_LIMIT=20) else (set OCR_LIMIT=%1)
python eval_ocr_app.py
pause
