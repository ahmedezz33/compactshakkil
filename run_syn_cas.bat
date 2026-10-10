@echo off
REM ============================================================
REM  تجربة السقف الأعلى (oracle): حقن الحالة الإعرابيّة من CAMeL
REM  تقيس: لو عُرِفت الحالة، كم تنخفض حركة الآخِر؟  (حدٌّ أعلى، تسريب مقصود)
REM  شغّل من جذر المشروع:  F:\Arabic\tashkil_project
REM ============================================================
chcp 65001 >nul
call venv\Scripts\activate.bat

echo.
echo [1/3] استخراج الحالة الإعرابيّة (feat=cas) — أوّل 220 ألف + val + test
python morph_extract.py data\processed_clean data\processed_clean_cas head=220000 feat=cas
if errorlevel 1 (echo   [خطأ] فشل استخراج cas & exit /b 1)

echo.
echo [2/3] صقل بالميزة الإعرابيّة  --^>  outputs_syn_cas
python scripts\train_syn.py --config configs\base_config_syn_cas.yaml
if errorlevel 1 (echo   [خطأ] فشل التدريب & exit /b 1)

echo.
echo [3/3] قياس (السقف الأعلى — حركة الآخِر مع معرفة الحالة)
python scripts\eval_syn.py outputs_syn_cas\best_model.pt data\processed_clean\test.txt data\processed_clean_cas\test.pos
echo.
echo ============================================================
echo  الصِق لي أسطر القياس: الفارق في حركة الآخِر = سقف ما تعطيه معرفة الحالة
echo ============================================================
pause
