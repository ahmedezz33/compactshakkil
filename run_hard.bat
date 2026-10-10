@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo [1/3] mine hard examples from FULL train (gold = truth)
python scripts\mine_hard.py outputs_v3_unified\latest.pt data\processed_clean\train.txt data\hard_train.txt 0 0.90
echo [2/3] fine-tune V3-unified with hard examples upweighted
python scripts\train_hard.py --config configs\config_hard.yaml
echo [3/3] evaluate on general test (case-ending split)
python scripts\eval_base_ce.py outputs_v3_hard\best_model.pt data\processed_clean\test.txt 4000
pause
