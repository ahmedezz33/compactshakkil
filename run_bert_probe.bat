@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo تثبيت transformers عند اللزوم...
pip install transformers -q
echo الاختبار الحاسم: هل CAMeLBERT يتنبّأ بالحالة أدقّ من 97.45%؟
echo (أوّل تشغيل ينزّل أوزان النموذج ~500MB)
python scripts\bert_case_probe.py CAMeL-Lab/bert-base-arabic-camelbert-ca data\processed_clean\train.txt data\processed_clean\test.txt 40000 2
pause
