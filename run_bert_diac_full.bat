@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo التدريب الكامل: مشكل CAMeLBERT (ساعات)
python scripts\train_bert_diac.py full
pause
