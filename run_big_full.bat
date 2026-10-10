@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo Training BIG 384x6 on FULL data from scratch (long: hours)
python scripts\train_full.py --config configs\config_big_full.yaml
echo Done. Send me outputs_big_full\best_model.pt for case-ending eval.
pause
