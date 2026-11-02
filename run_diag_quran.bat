@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
if "%N%"=="" set N=30
echo === quran retrieval diag ===
python diag_quran_retrieval.py
pause
