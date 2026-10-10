@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo تحقّق من gradio (تثبيتٌ عند اللزوم)...
pip install gradio -q
echo تشغيل التطبيق... سيفتح المتصفّح على http://127.0.0.1:7860
python app.py
pause
