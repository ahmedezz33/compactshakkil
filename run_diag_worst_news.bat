@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
if "%N_NEWS%"=="" set N_NEWS=150
echo === worst BERT news lines ===
python diag_worst_news.py
pause
