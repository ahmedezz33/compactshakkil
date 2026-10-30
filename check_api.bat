@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === diacritize (الحمد لله رب العالمين) ===
curl.exe -s -X POST http://127.0.0.1:8000/v1/diacritize -H "Content-Type: application/json" --data-binary @check_diac.json
echo.
echo === pronounce (مص الطفل ليده) ===
curl.exe -s -X POST http://127.0.0.1:8000/v1/pronounce -H "Content-Type: application/json" --data-binary @check_pron.json
echo.
pause
