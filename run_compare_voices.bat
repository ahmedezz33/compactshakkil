@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python compare_voices.py %*
pause
