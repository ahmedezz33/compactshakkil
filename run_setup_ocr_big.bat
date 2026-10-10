@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: ====== اختر النموذج حسب ذاكرة كرت الشاشة (VRAM) ======
:: 12GB+  : Qwen/Qwen2.5-VL-7B-Instruct
:: 6-8GB  : Qwen/Qwen2.5-VL-3B-Instruct   (اخفّ واضمن)
set "MODEL=Qwen/Qwen2.5-VL-3B-Instruct"
:: ====================================================
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
echo [1/3] تحديث المكتبات...
"%PY%" -m pip install -U "transformers==4.51.3" accelerate qwen-vl-utils pillow -q --disable-pip-version-check
"%PY%" -m pip install bitsandbytes -q --disable-pip-version-check
> ocr_model.txt echo %MODEL%
echo [2/3] تنزيل النموذج: %MODEL% (قد ياخذ وقتا وحجما كبيرا)...
"%PY%" download_ocr_model.py
if errorlevel 1 ( echo [خطأ] فشل التنزيل & pause & exit /b 1 )
echo [3/3] تمّ. شغّل: run_app_teach.bat
pause
