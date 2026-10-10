@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m pip install -q fastapi "uvicorn[standard]" python-multipart --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_LORA=outputs_ocr_unified
set API_PORT=8000
echo === CompactShakkil API على المنفذ %API_PORT% ===
echo الوثائق التفاعليّة: http://localhost:8000/docs
python -m uvicorn api_server:app --host 127.0.0.1 --port %API_PORT% --workers 1
pause
