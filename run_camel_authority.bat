@echo off
chcp 65001 >nul
call venv\Scripts\activate.bat
echo قياس جدوى السلطة الصرفيّة (مولّد CAMeL) مقابل النموذج على الاختبار
python scripts\camel_authority_eval.py outputs_v3_hard\best_model.pt data\processed_clean\test.txt 800
pause
