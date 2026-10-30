@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 ( echo [khata] venv & pause & exit /b 1 )
python -m pip install -q pillow arabic-reshaper python-bidi --disable-pip-version-check
if exist ocr_model.txt set /p OCR_MODEL=<ocr_model.txt
set "TXT=%~1"
if "%TXT%"=="" set "TXT=ذهب الطالب إلى المدرسة وقرأ الدرس"
echo === توليد فيديو تعليمي للنطق ===
python make_lesson_video.py --text "%TXT%" --out lesson.mp4
if errorlevel 1 ( echo [khata] generation & pause & exit /b 1 )
echo.
echo تم: lesson.mp4
pause
