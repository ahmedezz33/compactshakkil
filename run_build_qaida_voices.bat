@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
pip install edge-tts imageio-ffmpeg -q --disable-pip-version-check
python build_qaida_voices.py %*
pause
