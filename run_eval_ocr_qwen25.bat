@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
python -m pip install -q qwen-vl-utils --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_PREPROCESS=0
set OCR_MAX_SIDE=1600
if "%OCR_LIMIT%"=="" set OCR_LIMIT=20
echo === مقارنة OCR: Qari مقابل Qwen2.5-VL-3B (صفحات=%OCR_LIMIT%) ===
echo (تنزيل Qwen اول مرة ~7GB)
python eval_ocr_qwen25.py
pause
