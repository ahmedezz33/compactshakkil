@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python data\build_maxdata.py
pause
