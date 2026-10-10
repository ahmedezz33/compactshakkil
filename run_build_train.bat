@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python build_train_dataset.py %*
pause
