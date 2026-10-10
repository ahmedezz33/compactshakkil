@echo off
REM ============================================================
REM  التنظيف الاصطلاحيّ + إعادة صقل V3-unified  (CompactShakkil)
REM  شغّله من جذر المشروع:  F:\Arabic\tashkil_project
REM  ضع:  normalize_conventions.py        في الجذر
REM       configs\base_config_v3_unified_norm.yaml
REM       scripts\train_v3_unified.py     (موجود مسبقًا)
REM ============================================================
chcp 65001 >nul
setlocal

echo.
echo [1/2] التنظيف الاصطلاحيّ: processed_clean  --^>  processed_clean_norm
echo       (لام «ال» القمريّة العارية = سكون ، همزة إلى/إذا/إذ = كسرة)
python normalize_conventions.py data\processed_clean data\processed_clean_norm
if errorlevel 1 (echo   [خطأ] فشل التطبيع & exit /b 1)

echo.
echo [2/2] إعادة الصقل الموحّد على البيانات المُطبَّعة  --^>  outputs_v3_unified_norm
python scripts\train_v3_unified.py --config configs\base_config_v3_unified_norm.yaml
if errorlevel 1 (echo   [خطأ] فشل التدريب & exit /b 1)

echo.
echo ============================================================
echo  تمّ. النموذج المُطبَّع في:  outputs_v3_unified_norm\latest.pt
echo  أرسِله إليّ (أو انسخه للمشروع) لأقيس DER على test المُطبَّع
echo  وأقارنه بالنسخة الحاليّة.
echo ============================================================
endlocal
pause
