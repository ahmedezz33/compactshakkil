@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo [1/4] control from scratch (no feature)
python scripts\train_syn.py --config configs\config_scratch_ctrl.yaml
echo [2/4] eval control
python scripts\eval_syn.py outputs_scratch_ctrl\best_model.pt data\processed_clean\test.txt data\processed_clean_oracle\test.pos
echo [3/4] from scratch WITH oracle case-family
python scripts\train_syn.py --config configs\config_oracle_scratch.yaml
echo [4/4] eval oracle
python scripts\eval_syn.py outputs_scratch_oracle\best_model.pt data\processed_clean\test.txt data\processed_clean_oracle\test.pos
echo ==== compare: control vs oracle (case-ending is the number) ====
pause
