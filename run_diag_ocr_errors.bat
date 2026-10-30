@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_PREPROCESS=0
if "%OCR_LIMIT%"=="" set OCR_LIMIT=20
echo === تفكيكُ خطأ OCR (كامل / مجرّد / استرجاع) — صفحات=%OCR_LIMIT% ===
python diag_ocr_errors.py
pause
