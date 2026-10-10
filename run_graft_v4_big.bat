@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
python scripts\train_bert_graft.py max outputs_v4_big\best_model.pt outputs_bert_graft_big
pause
