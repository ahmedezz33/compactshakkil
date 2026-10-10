@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
pip install gradio "transformers>=4.49" gtts edge-tts imageio-ffmpeg python-docx -q --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set OCR_LORA=outputs_ocr_unified
set GRADIO_SERVER_NAME=0.0.0.0
set GRADIO_SERVER_PORT=7860
python app_teach.py
pause
