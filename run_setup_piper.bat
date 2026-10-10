@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
pip install piper-tts -q --disable-pip-version-check
python get_piper_voice.py
pause
