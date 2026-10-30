@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if "%1"=="" (set SEM_MAX=80) else (set SEM_MAX=%1)
python measure_semantic_gen.py
pause
