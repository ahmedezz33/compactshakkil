@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo === Batch OCR a whole book to diacritized text ===
echo Usage examples:
echo   run_extract_book.bat --author "0179 ..." --book "..." 
echo   run_extract_book.bat --pdf "F:\shamela4\pdf\...\book.pdf" --dpi 300 --skip 3
python -X utf8 extract_book.py %*
echo.
pause
