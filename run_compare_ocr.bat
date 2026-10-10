chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
if "%~1"=="" (set "IMG=_inspect\page_26.png") else (set "IMG=%~1")
set OCR_4BIT=0
set OCR_DEVICE=gpu
python compare_ocr.py "%IMG%"
pause
