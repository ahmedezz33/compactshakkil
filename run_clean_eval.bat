@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo [1/3] بناء اختبار خالٍ من التسرّب
python scripts\make_clean_test.py
echo [2/3] قياس الاساس v3-hard على الاختبار النظيف
python scripts\eval_base_ce.py outputs_v3_hard\best_model.pt data\processed_clean\test_noleak.txt 5000
echo [3/3] قياس BERT-graft على الاختبار النظيف
python scripts\eval_graft.py data\processed_clean\test_noleak.txt 5000
echo ==== قارن: هل تصمد فجوة BERT-graft على البيانات النظيفة؟ ====
pause
