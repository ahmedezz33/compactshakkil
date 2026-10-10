@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo تجربة سريعة (300 جملة، 20 خطوة) لالتقاط أي خطأ قبل التدريب الكامل
python scripts\train_bert_diac.py smoke
pause
