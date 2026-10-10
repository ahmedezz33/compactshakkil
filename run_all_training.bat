@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo ===== START %date% %time% ===== > train_log.txt
echo [1/3] download + dataset >> train_log.txt 2>^&1
python -X utf8 build_train_dataset.py >> train_log.txt 2>^&1
echo [2/3] rebuild metadata (F5 format) >> train_log.txt 2>^&1
python -X utf8 build_train_dataset.py --skip-download >> train_log.txt 2>^&1
echo [3/3] finetune >> train_log.txt 2>^&1
python -X utf8 finetune_f5.py >> train_log.txt 2>^&1
echo ===== DONE %date% %time% ===== >> train_log.txt 2>^&1
echo تمّ. راجِع train_log.txt
pause
