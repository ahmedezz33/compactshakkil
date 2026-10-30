@echo off
chcp 65001 >nul
cd /d "%~dp0"
set STAMP=%date:~-4%%date:~3,2%%date:~0,2%
set DEST=backups\%STAMP%
if not exist backups mkdir backups
if not exist "%DEST%" mkdir "%DEST%"
echo النسخُ إلى %DEST% ...
copy /Y outputs_bert_graft\best_model.pt "%DEST%\" >nul 2>&1
copy /Y api_keys.json "%DEST%\" >nul 2>&1
copy /Y api_usage.log "%DEST%\" >nul 2>&1
copy /Y admin_token.txt "%DEST%\" >nul 2>&1
copy /Y name_overrides.json "%DEST%\" >nul 2>&1
copy /Y fixed_forms.json "%DEST%\" >nul 2>&1
copy /Y semantic_config.json "%DEST%\" >nul 2>&1
copy /Y ocr_model.txt "%DEST%\" >nul 2>&1
echo تمّ. المحتوى:
dir "%DEST%"
pause
