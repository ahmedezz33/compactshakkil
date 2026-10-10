@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python fix_f5_torch.py
pause
