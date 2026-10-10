@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo Installing Piper (neural voice + bundled eSpeak phonemizer) ...
python -m pip install --quiet piper-tts onnxruntime numpy
echo Downloading Arabic Piper voice (ar_JO-kareem-medium) ...
python download_piper_voice.py %*
echo.
echo Done. Restart the app, choose the Piper voice, and press speak.
pause
