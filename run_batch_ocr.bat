@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if "%~1"=="" ( echo اسحب ملف PDF على هذا الباتش او مرّره كوسيط & pause & exit /b 1 )
"%PY%" batch_ocr.py %* 
pause
