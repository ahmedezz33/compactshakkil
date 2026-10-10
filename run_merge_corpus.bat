@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo Building augmented diacritization corpus (Tashkeela + Shamela) ...
python merge_corpus.py
echo.
echo Done -> data\processed_ft\train.txt
pause
