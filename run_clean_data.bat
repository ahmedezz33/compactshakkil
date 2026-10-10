@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
echo === Cleaning TEST set ===
"%PY%" clean_corpus.py data\processed_clean\test_noleak.txt data\processed_clean\test_clean.txt
echo.
echo === Cleaning TRAIN corpus (large, be patient) ===
"%PY%" clean_corpus.py data\processed_max\train.txt data\processed_max\train_clean.txt
echo.
echo Done. Clean files: data\processed_clean\test_clean.txt , data\processed_max\train_clean.txt
pause
