@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo ================================================
echo   Setup Arabic OCR (QARI-OCR / Qwen2-VL 2B)
echo ================================================
python -m pip install --upgrade qwen-vl-utils
python -m pip install --upgrade pypdfium2
python -c "import torchvision" 2>nul || python -m pip install torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
echo.
echo Deps ready. The QARI-OCR model (~4.5GB) downloads on first use in the app.
echo You can pre-download it now (optional):
python -X utf8 -c "import ocr_engine as o; print('available:', o.available())"
echo.
pause
