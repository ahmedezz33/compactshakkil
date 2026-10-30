@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo اعادة تحميل Caddy بالتهيئة الجديدة (بلا ايقاف الخدمة)...
caddy.exe.exe reload --config deploy\Caddyfile --adapter caddyfile
if %errorlevel%==0 (echo تم بنجاح - تم حجب /admin من الانترنت) else (echo فشل الريلود - التهيئة القديمة ما زالت تعمل بامان)
pause
