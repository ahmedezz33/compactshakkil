chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
if "%~1"=="" (set "IMG=_inspect\page_26.png") else (set "IMG=%~1")
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_4BIT=1
set OCR_DEVICE=offload
python diag_ocr.py "%IMG%"
pause
