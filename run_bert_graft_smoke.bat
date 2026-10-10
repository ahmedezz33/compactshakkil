@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python scripts\train_bert_graft.py smoke
pause
