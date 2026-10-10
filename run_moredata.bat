@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo Fine-tune V3-unified on FULL clean data (~1.15M) + Quran
python scripts\train_hard.py --config configs\config_moredata.yaml
echo Evaluate (case-ending split)
python scripts\eval_base_ce.py outputs_v3_moredata\best_model.pt data\processed_clean\test.txt 4000
pause
