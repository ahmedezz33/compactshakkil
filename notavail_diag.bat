@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
set BENCH_N=400
python notavail_diag.py
pause
