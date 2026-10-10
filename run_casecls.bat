@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo [1/3] regenerate oracle case-family labels (420k train, fast, no CAMeL)
python oracle_case_extract.py data\processed_clean data\processed_clean_oracle head=420000
echo [2/3] train case-family classifier (specialist, from scratch)
python scripts\train_casecls.py --config configs\config_casecls.yaml
echo [3/3] measure family accuracy vs base bar (97.45%)
python scripts\eval_casecls.py outputs_casecls\best_model.pt data\processed_clean\test.txt data\processed_clean_oracle\test.pos
pause
