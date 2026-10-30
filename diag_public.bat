@echo off
chcp 65001 >nul
echo ================================================
echo [1] عنوان الجهاز المحلي (قارنه بتوجيه الراوتر 192.168.100.192)
ipconfig | findstr /i "IPv4"
echo.
echo [2] هل يستمع المنافذ 443 (Caddy) / 80 / 8000 (uvicorn)؟
netstat -an | findstr ":443" | findstr LISTENING
netstat -an | findstr ":8000" | findstr LISTENING
netstat -an | findstr /R /C:":80 " | findstr LISTENING
echo (اذا لم يظهر 443 فمعناه Caddy متوقف)
echo.
echo [3] حالة الخدمات
sc query CompactShakkilAPI | findstr STATE
sc query Caddy | findstr STATE
sc query caddy | findstr STATE
echo.
echo [4] اخر نتيجة DuckDNS
type deploy\duckdns_last.txt
echo.
pause
