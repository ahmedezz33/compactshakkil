@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_LORA=outputs_ocr_unified
set API_PORT=8000
python -m uvicorn api_server:app --host 127.0.0.1 --port %API_PORT% --workers 1
