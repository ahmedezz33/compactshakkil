@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python setup_f5.py %*
pause
