@echo off
REM run_clean_pipeline.bat — انقر نقرًا مزدوجًا لتشغيل: تنظيف -> توسيع الرأس -> صقل.
cd /d "F:\Arabic\tashkil_project"
set PYTHONIOENCODING=utf-8
call "venv\Scripts\activate.bat"
echo === بدء الأنبوب %date% %time% === > pipeline_log.txt
echo === [1/3] تنظيف البيانات === >> pipeline_log.txt
python clean_data.py data/processed data/processed_clean 0.99 keep >> pipeline_log.txt 2>&1
echo === [2/3] توسيع الراس 15-^>19 === >> pipeline_log.txt
python expand_head.py >> pipeline_log.txt 2>&1
echo === [3/3] الصقل النظيف === >> pipeline_log.txt
python scripts\train_v1_clean.py --config configs\base_config_v1_clean.yaml >> pipeline_log.txt 2>&1
echo === انتهى الأنبوب %date% %time% === >> pipeline_log.txt
echo تم. يمكنك اغلاق النافذة.
pause
