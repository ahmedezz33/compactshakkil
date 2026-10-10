@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" ensemble_eval.py %*
pause
