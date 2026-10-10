@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo Generating F5 jalalah A/B samples (needs GPU) ...
python gen_f5_jalalah.py
echo.
echo Listen to samples_f5\*.wav
pause
