# run_clean_pipeline.ps1 — الأساس النظيف: تنظيف → توسيع الرأس → صقل، بأمر واحد.
# التشغيل:  powershell -ExecutionPolicy Bypass -File .\run_clean_pipeline.ps1
$ErrorActionPreference = "Stop"
Set-Location "F:\Arabic\tashkil_project"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Log($m) { $m | Tee-Object -FilePath pipeline_log.txt -Append }

"=== بدء الأنبوب $(Get-Date -Format o) ===" | Out-File pipeline_log.txt -Encoding utf8

& ".\venv\Scripts\Activate.ps1"

Log "=== [1/3] تنظيف البيانات ==="
python clean_data.py data/processed data/processed_clean 0.99 keep 2>&1 | Tee-Object -FilePath pipeline_log.txt -Append

Log "=== [2/3] توسيع الرأس 15->19 ==="
python expand_head.py 2>&1 | Tee-Object -FilePath pipeline_log.txt -Append

Log "=== [3/3] الصقل النظيف ==="
python scripts/train_v1_clean.py --config configs/base_config_v1_clean.yaml 2>&1 | Tee-Object -FilePath pipeline_log.txt -Append

Log "=== انتهى الأنبوب $(Get-Date -Format o) ==="
