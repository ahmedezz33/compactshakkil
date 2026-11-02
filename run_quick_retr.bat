@echo off
chcp 65001 >nul
cd /d %~dp0
call venv\Scripts\activate.bat
python quick_retr_check.py data\quran_retr_sample.txt
pause
