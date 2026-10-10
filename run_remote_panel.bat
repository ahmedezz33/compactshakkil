@echo off
cd /d "%~dp0"
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m pip install flask mss pyautogui pillow cryptography -q --disable-pip-version-check
"%PY%" remote_panel.py
pause
