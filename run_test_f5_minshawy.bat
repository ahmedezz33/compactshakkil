@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo === اختبار صوت المنشاويّ المصقول (F5) ===
python -X utf8 f5_engine.py "قُلْ هُوَ اللَّهُ أَحَدٌ. اللَّهُ الصَّمَدُ. لَمْ يَلِدْ وَلَمْ يُولَدْ. وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ."
echo.
echo تمّ. الملف: f5_test.wav
start "" f5_test.wav
pause
