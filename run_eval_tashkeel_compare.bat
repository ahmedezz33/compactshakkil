@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
python -m pip install -q catt-tashkeel python-docx --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
if "%N_NEWS%"=="" set N_NEWS=150
if "%N_CLASS%"=="" set N_CLASS=100
if "%CATT_MODEL%"=="" set CATT_MODEL=ed
set DEBUG=1
echo === compare tashkeel (clean + both metrics + CATT-ED) ===
python eval_tashkeel_compare.py
pause
