@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo i'rab-focused fine-tune (targets case-ending errors, up-weights final positions).
echo Runs on existing Tashkeela data - no OCR needed. Resumes from current model.
echo Saves to outputs_bert_graft_ft (your working model is NOT touched).
python finetune_diac.py %*
echo.
echo Watch the 'final' number in the eval - that is the i'rab (case-ending) error.
echo If it dropped, copy outputs_bert_graft_ft\best_model.pt over outputs_bert_graft\best_model.pt
pause
