@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python gen_piper_jalalah.py
echo.
echo Listen to samples_piper_jalalah\*.wav
pause
