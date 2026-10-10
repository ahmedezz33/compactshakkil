@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo [1/4] control 256x4 (3.25M) from scratch, no feature
python scripts\train_syn.py --config configs\config_cap_ctrl.yaml
echo [2/4] eval control (case-ending split)
python scripts\eval_syn.py outputs_cap_ctrl\best_model.pt data\processed_clean\test.txt data\processed_clean_oracle\test.pos
echo [3/4] BIG 384x6 (~11M) from scratch, no feature
python scripts\train_syn.py --config configs\config_cap_big.yaml
echo [4/4] eval BIG (case-ending split)
python scripts\eval_syn.py outputs_cap_big\best_model.pt data\processed_clean\test.txt data\processed_clean_oracle\test.pos
echo ==== compare control 256x4 vs BIG 384x6 : does capacity cut case-ending? ====
pause
