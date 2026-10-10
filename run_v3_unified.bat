@echo off
REM run_v3_unified.bat — صقل V3-unified (مزيج عامّ+قرآن). نقر مزدوج للتشغيل.
cd /d "F:\Arabic\tashkil_project"
set PYTHONIOENCODING=utf-8
call "venv\Scripts\activate.bat"
echo === V3-unified بدء %date% %time% === > v3_unified_log.txt
python scripts\train_v3_unified.py --config configs\base_config_v3_unified.yaml >> v3_unified_log.txt 2>&1
echo === انتهى %date% %time% === >> v3_unified_log.txt
echo تم. يمكنك اغلاق النافذة.
pause
