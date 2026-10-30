@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem اعادة تحميل منطق الـ API بعد اي تعديل - محليا بلا صلاحية مسؤول
set /p TOK=<admin_token.txt
curl.exe -s -X POST http://127.0.0.1:8000/admin/reload -H "X-Admin-Token: %TOK%"
echo.
pause
