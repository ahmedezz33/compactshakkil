@echo off
setlocal
cd /d "%~dp0"
set "SRC=outputs_bert_graft_ft\best_model.pt"
set "DST=outputs_bert_graft\best_model.pt"
set "BK=outputs_bert_graft\best_model.backup.pt"

if not exist "%SRC%" ( echo [ERROR] fine-tuned model not found: %SRC% & pause & exit /b 1 )
if not exist "%DST%" ( echo [ERROR] current model not found: %DST% & pause & exit /b 1 )

if not exist "%BK%" (
  echo Backing up ORIGINAL model to %BK%
  copy /Y "%DST%" "%BK%" >nul || ( echo [ERROR] backup failed & pause & exit /b 1 )
) else (
  echo Backup already exists ^(keeping original^): %BK%
)

echo Deploying fine-tuned model ^(DER 1.04%%^)...
copy /Y "%SRC%" "%DST%" >nul || ( echo [ERROR] deploy failed & pause & exit /b 1 )

echo.
echo [OK] Deployed. Rollback backup: %BK%
echo Now RESTART the app to load the new model.
pause
