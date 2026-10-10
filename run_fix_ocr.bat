chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
if "%~1"=="" (set "IMG=_inspect\page_26.png") else (set "IMG=%~1")
echo === ارجاع transformers الى 4.51.3 (نسخة مجربة) ===
python -m pip install "transformers==4.51.3" "tokenizers>=0.21,<0.22" -q --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_4BIT=1
set OCR_DEVICE=offload
echo === تشخيص على: %IMG% ===
python diag_ocr.py "%IMG%"
pause
