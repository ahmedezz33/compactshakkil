@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo === Building lafz al-jalala clips with edge (same voice, isolated) ===
python -X utf8 build_lafz_edge.py
echo.
pause
