chcp 65001>nul
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
set ADAPT_EPOCHS=2
python adapt_news.py
pause
