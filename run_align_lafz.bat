@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo === Extracting lafz al-jalala via forced alignment ===
python -X utf8 align_lafz.py
echo.
echo === finished. See recordings\lafz\ ===
pause
