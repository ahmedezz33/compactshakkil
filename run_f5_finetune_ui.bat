@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo تثبيت bitsandbytes (لموفّر ذاكرة 8-bit Adam) ...
pip install bitsandbytes >/dev/null 2>&1
echo تشغيل واجهة صقل F5 — افتح الرابط في المتصفّح
f5-tts_finetune-gradio || python -m f5_tts.train.finetune_gradio
pause
