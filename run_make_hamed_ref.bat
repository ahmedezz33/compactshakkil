@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python make_hamed_reference.py
pause
