@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if "%1"=="" (set BENCH_N=3000) else (set BENCH_N=%1)
python bert_first.py
pause
