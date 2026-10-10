@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo [1/3] oracle case-family extraction (no CAMeL)
python oracle_case_extract.py data\processed_clean data\processed_clean_oracle head=220000
echo [2/3] fine-tune with oracle feature
python scripts\train_syn.py --config configs\base_config_syn_oracle.yaml
echo [3/3] measure (true upper bound)
python scripts\eval_syn.py outputs_syn_oracle\best_model.pt data\processed_clean\test.txt data\processed_clean_oracle\test.pos
pause
