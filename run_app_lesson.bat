@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
python -m pip install -q gradio pillow arabic-reshaper python-bidi --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
echo === واجهة مولّد فيديوهات النطق (المتصفّح: http://127.0.0.1:7862) ===
python app_lesson.py
pause
