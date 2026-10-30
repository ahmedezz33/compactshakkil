@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo [!] شغّل هذا الباتّ كمسؤول: انقر يمينًا ثمّ "Run as administrator"
  pause
  exit /b
)
echo ايقاف الخدمة...
net stop CompactShakkilAPI
echo تشغيل الخدمة...
net start CompactShakkilAPI
echo.
echo تمّت اعادة التشغيل. جرّب الان القرآن في المنصّة.
pause
