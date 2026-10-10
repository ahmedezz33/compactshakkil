@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -X utf8 compare_jalalah4.py
echo.
echo Listen to files in recordings\jalalah_test4
pause
