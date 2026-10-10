@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python scripts\check_overlap.py
pause
