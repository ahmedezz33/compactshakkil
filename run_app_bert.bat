@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
pip install gradio transformers -q
python app_bert.py
pause
