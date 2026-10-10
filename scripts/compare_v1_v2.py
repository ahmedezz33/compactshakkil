"""
سكربت المقارنة الشامل بين V1 و V2.

يشغّل التقييمَين على test.txt ويعرض جدول مقارنة نهائيّ + يحفظ النتائج JSON.

الاستخدام:
    python scripts\compare_v1_v2.py

الملفّات المطلوبة:
    - compactshakkil_v1_baseline\best_model.pt
    - outputs_v2\best_model.pt
    - data\processed\test.txt

المخرجات:
    - outputs\evaluation_v1.json
    - outputs_v2\evaluation_v2.json
    - comparison_results.md (جدول جاهز للورقة)
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# مسارات الملفّات
V1_CHECKPOINT = "compactshakkil_v1_baseline/best_model.pt"
V2_CHECKPOINT = "outputs_v2/best_model.pt"
V1_RESULTS = "outputs/evaluation_v1.json"
V2_RESULTS = "outputs_v2/evaluation_v2.json"
COMPARISON_FILE = "comparison_results.md"

def check_files():
    """التحقّق من وجود الملفّات المطلوبة."""
    required = [V1_CHECKPOINT, V2_CHECKPOINT, "data/processed/test.txt"]
    missing = [f for f in required if not Path(f).exists()]
    if missing:
        print("❌ ملفّات مفقودة:")
        for f in missing:
            print(f"   - {f}")
        return False
    print("✅ كل الملفّات المطلوبة موجودة")
    return True

def evaluate_v1():
    """تقييم V1 على test.txt."""
    print("\n" + "="*60)
    print("🔵 تقييم V1 (Baseline)")
    print("="*60)
    
    start = time.time()
    result = subprocess.run([
        sys.executable, "-X", "utf8", "scripts/evaluate.py",
        "--checkpoint", V1_CHECKPOINT,
        "--split", "test",
        "--batch_size", "32"
    ], capture_output=True, text=True, encoding="utf-8")
    elapsed = time.time() - start
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ خطأ في تقييم V1:\n{result.stderr}")
        return None
    
    # استخراج المقاييس من المخرجات
    metrics = parse_metrics(result.stdout)
    metrics["time_seconds"] = elapsed
    metrics["model"] = "V1"
    
    # حفظ JSON
    Path("outputs").mkdir(exist_ok=True)
    with open(V1_RESULTS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"💾 حُفظت نتائج V1 في: {V1_RESULTS}")
    
    return metrics

def evaluate_v2():
    """تقييم V2 على test.txt."""
    print("\n" + "="*60)
    print("🟢 تقييم V2 (with Quran)")
    print("="*60)
    
    start = time.time()
    result = subprocess.run([
        sys.executable, "-X", "utf8", "scripts/evaluate_v2.py",
        "--checkpoint", V2_CHECKPOINT,
        "--split", "test",
        "--batch_size", "32"
    ], capture_output=True, text=True, encoding="utf-8")
    elapsed = time.time() - start
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ خطأ في تقييم V2:\n{result.stderr}")
        return None
    
    metrics = parse_metrics(result.stdout)
    metrics["time_seconds"] = elapsed
    metrics["model"] = "V2"
    
    Path("outputs_v2").mkdir(exist_ok=True)
    with open(V2_RESULTS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"💾 حُفظت نتائج V2 في: {V2_RESULTS}")
    
    return metrics

def parse_metrics(output):
    """استخراج المقاييس من مخرجات evaluate.py."""
    metrics = {}
    for line in output.split("\n"):
        line = line.strip()
        if "إجمالي الحروف:" in line:
            metrics["total_letters"] = int(line.split(":")[1].strip().replace(",", ""))
        elif "إجمالي الكلمات:" in line:
            metrics["total_words"] = int(line.split(":")[1].strip().replace(",", ""))
        elif "DER" in line and "بلا" not in line and "Diacritic Error Rate" in line:
            val = line.split(":")[-1].strip().rstrip("%")
            metrics["DER"] = float(val)
        elif "DER-CE" in line:
            val = line.split(":")[-1].strip().rstrip("%")
            metrics["DER_CE"] = float(val)
        elif "WER" in line and "بلا" not in line and "Word Error Rate" in line:
            val = line.split(":")[-1].strip().rstrip("%")
            metrics["WER"] = float(val)
        elif "WER-CE" in line:
            val = line.split(":")[-1].strip().rstrip("%")
            metrics["WER_CE"] = float(val)
    return metrics

def generate_comparison_report(v1, v2):
    """إنشاء تقرير المقارنة النهائيّ."""
    print("\n" + "="*60)
    print("📊 مقارنة V1 vs V2 — النتائج النهائية")
    print("="*60)
    
    metrics_list = [
        ("DER (%)", "DER", "lower_is_better"),
        ("DER-CE (%)", "DER_CE", "lower_is_better"),
        ("WER (%)", "WER", "lower_is_better"),
        ("WER-CE (%)", "WER_CE", "lower_is_better"),
        ("Time (s)", "time_seconds", "lower_is_better"),
    ]
    
    # جدول للطباعة
    header = f"{'Metric':<15} | {'V1':>10} | {'V2':>10} | {'Δ':>10} | {'Winner':>8}"
    separator = "-" * len(header)
    print(f"\n{header}")
    print(separator)
    
    md_lines = [
        "# مقارنة V1 vs V2 على test.txt",
        f"\n**تاريخ التقييم**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"\n**عدد القطع المُقيَّمة**: {v1.get('total_letters', 'N/A'):,} حرف / {v1.get('total_words', 'N/A'):,} كلمة",
        "\n## النتائج التفصيلية\n",
        "| Metric | V1 (Baseline) | V2 (with Quran) | Δ (تحسّن) | Winner |",
        "|:-------|:-------------:|:---------------:|:---------:|:------:|",
    ]
    
    v2_wins = 0
    v1_wins = 0
    
    for label, key, direction in metrics_list:
        v1_val = v1.get(key, 0)
        v2_val = v2.get(key, 0)
        delta = v2_val - v1_val
        
        if direction == "lower_is_better":
            winner = "🏆 V2" if v2_val < v1_val else ("🏆 V1" if v1_val < v2_val else "= تعادل")
            if v2_val < v1_val:
                v2_wins += 1
            elif v1_val < v2_val:
                v1_wins += 1
        
        delta_str = f"{delta:+.3f}"
        line = f"{label:<15} | {v1_val:>10.3f} | {v2_val:>10.3f} | {delta_str:>10} | {winner:>8}"
        print(line)
        
        md_lines.append(f"| {label} | {v1_val:.3f} | {v2_val:.3f} | {delta_str} | {winner} |")
    
    print(separator)
    print(f"\n🎯 V2 ربحت في {v2_wins} من {len(metrics_list)} مقاييس")
    print(f"🎯 V1 ربحت في {v1_wins} من {len(metrics_list)} مقاييس")
    
    md_lines.extend([
        f"\n## ملخّص\n",
        f"- **V2 تفوّقت في**: {v2_wins} من {len(metrics_list)} مقاييس",
        f"- **V1 تفوّقت في**: {v1_wins} من {len(metrics_list)} مقاييس",
    ])
    
    if v2_wins > v1_wins:
        conclusion = "**النتيجة**: V2 (مع دمج القرآن) تُظهر تحسّنًا واضحًا مقارنة بـ V1."
    elif v1_wins > v2_wins:
        conclusion = "**النتيجة**: V1 (Baseline) أفضل — دمج القرآن لم يُحسّن الأداء على Tashkeela."
    else:
        conclusion = "**النتيجة**: النموذجان متكافئان في الأداء."
    
    md_lines.append(f"\n{conclusion}")
    
    # حفظ Markdown
    with open(COMPARISON_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"\n💾 تقرير المقارنة الكامل في: {COMPARISON_FILE}")

def main():
    print("="*60)
    print("🚀 مقارنة CompactShakkil V1 vs V2")
    print("="*60)
    
    if not check_files():
        return
    
    v1_metrics = evaluate_v1()
    if v1_metrics is None:
        return
    
    v2_metrics = evaluate_v2()
    if v2_metrics is None:
        return
    
    generate_comparison_report(v1_metrics, v2_metrics)
    
    print("\n✅ اكتملت المقارنة!")

if __name__ == "__main__":
    main()
