@echo off
REM ============================================================
REM  تجربة الإشارة النحويّة (POS) — طيّار سريع  CompactShakkil-Syn
REM  شغّل من جذر المشروع:  F:\Arabic\tashkil_project
REM  المتطلّبات: venv فيه camel_tools (المُستخدَم في verify_root_source.py)
REM  الملفّات: morph_features.py, morph_extract.py (الجذر)
REM            models\transformer_syn.py, scripts\train_syn.py, scripts\eval_syn.py
REM            configs\base_config_syn.yaml
REM ============================================================
chcp 65001 >nul
call venv\Scripts\activate.bat

echo.
echo [1/3] استخراج POS (أوّل 220 ألف سطر تدريب + val + test كاملَين)
python morph_extract.py data\processed_clean data\processed_clean_pos head=220000
if errorlevel 1 (echo   [خطأ] فشل استخراج POS ^(تأكّد من camel_tools^) & exit /b 1)

echo.
echo [2/3] صقل نحويّ من V3-unified  --^>  outputs_syn_pilot
python scripts\train_syn.py --config configs\base_config_syn.yaml
if errorlevel 1 (echo   [خطأ] فشل التدريب & exit /b 1)

echo.
echo [3/3] قياس (فصل حركة الآخِر عن البنية)
python scripts\eval_syn.py outputs_syn_pilot\best_model.pt data\processed_clean\test.txt data\processed_clean_pos\test.pos
echo.
echo ============================================================
echo  تمّ الطيّار. أرسِل إليّ الأرقام (أو best_model.pt + test.pos)
echo  لأقارن حركة الآخِر قبل/بعد الإشارة النحويّة.
echo ============================================================
pause
