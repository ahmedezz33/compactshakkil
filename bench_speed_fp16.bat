@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
set GRAFT_FP16=1
python bench_speed.py
pause
