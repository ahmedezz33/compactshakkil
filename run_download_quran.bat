@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python download_quran_audio.py %*
pause
