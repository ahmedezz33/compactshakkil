@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo === Step 1: make a 300-line sample from your test set ===
python bench_diac.py --make-sample 300
echo.
echo === Step 2: run YOUR model on the sample (CPU, won't disturb training) ===
python bench_ours.py
echo.
echo === Step 3: score YOUR model ===
python bench_diac.py --score bench_pred_ours.txt
echo.
echo Now diacritize bench_bare.txt with a rival (Claude/Gemini/CATT), save as bench_pred.txt,
echo then run:  python bench_diac.py --score bench_pred.txt
pause
