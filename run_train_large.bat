@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
echo ====================================================
echo  Large-base experiment: AraBERT-large v02 graft
echo  First run downloads ~1.4GB model (needs internet).
echo  Isolated: saves to outputs_bert_graft_large (your live model untouched).
echo  If you get CUDA out-of-memory, re-run as:  run_train_large.bat 3
echo ====================================================
"%PY%" train_graft_large.py %*
pause
