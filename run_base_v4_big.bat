@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python scripts\train_hard.py --config configs\config_v4_big.yaml
pause
