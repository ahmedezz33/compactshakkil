"""
معالج شامل لكل الجذور الجوف في المعجم — مع تدقيق يدوي.

المخرجات:
    1. lexicon/resolved_roots.tsv       — كل الجذور مع الحلول (قابل للاستيراد لـ Excel)
    2. lexicon/manual_review.tsv        — الجذور المشكوكة للمراجعة اليدوية
    3. lexicon/resolution_stats.txt     — تقرير إحصائي مفصّل
    4. lexicon/arabic_lexicon_clean.db  — معجم نظيف بدون # (بعد المراجعة)

سير العمل:
    1. شغّل هذا السكربت → يحلّل كل الجذور
    2. راجع manual_review.tsv بنفسك (افتحه في Excel)
    3. صحّح الاقتراحات → احفظ الملفّ
    4. شغّل apply_manual_review.py (لاحقًا) → يُنشئ المعجم النهائي
"""

import sqlite3
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from jawf_handler import JawfHandler

DB_PATH = 'lexicon/arabic_lexicon.db'
OUTPUT_DIR = Path('lexicon')

# ═══════════════════════════════════════════════════════════
# عتبات التصنيف
# ═══════════════════════════════════════════════════════════
CONFIDENCE_HIGH = 0.80    # ≥ 80% → مقبول تلقائيًا
CONFIDENCE_MED  = 0.60    # 60-80% → مراجعة موصى بها
# < 60% → مراجعة إلزامية


def get_all_hollow_roots():
    """جلب كل الجذور الجوف مع عدد مشتقّاتها وعيّنة كلمات."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # كل جذر فيه # مع عدد مشتقّاته
    c.execute("""
        SELECT root, COUNT(*) as derivative_count
        FROM roots
        WHERE root LIKE '%#%'
        GROUP BY root
        ORDER BY derivative_count DESC
    """)

    roots_data = []
    for root, count in c.fetchall():
        # عيّنة من 5 كلمات لكل جذر (للمراجعة اليدوية)
        c.execute("""
            SELECT DISTINCT w.word
            FROM words w
            JOIN roots r ON w.id = r.word_id
            WHERE r.root = ?
            ORDER BY w.frequency DESC
            LIMIT 5
        """, (root,))
        sample_words = [row[0] for row in c.fetchall()]

        roots_data.append({
            "root": root,
            "count": count,
            "samples": sample_words
        })

    conn.close()
    return roots_data


def classify_result(result: dict) -> str:
    """تصنيف النتيجة إلى: accepted / suggested / manual_required."""
    source = result.get("source", "failed")
    confidence = result.get("confidence", 0.0)

    if source == "gold":
        return "accepted"
    elif source == "rules" and confidence >= CONFIDENCE_HIGH:
        return "accepted"
    elif source == "rules" and confidence >= CONFIDENCE_MED:
        return "suggested"
    elif source == "statistical" and confidence >= CONFIDENCE_HIGH:
        return "suggested"
    else:
        return "manual_required"


def main():
    print("=" * 70)
    print("معالجة شاملة لكل الجذور الجوف مع تدقيق يدوي")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. جلب كل الجذور
    print("\n[1/4] جلب كل الجذور الجوف من المعجم...")
    roots_data = get_all_hollow_roots()
    print(f"      إجمالي الجذور الجوف: {len(roots_data):,}")
    total_derivatives = sum(r["count"] for r in roots_data)
    print(f"      إجمالي المشتقّات المتأثّرة: {total_derivatives:,}")

    # 2. المعالجة
    print(f"\n[2/4] معالجة كل جذر (3 مستويات)...")
    handler = JawfHandler(DB_PATH)

    all_results = []
    stats = {
        "accepted": [],
        "suggested": [],
        "manual_required": [],
    }
    source_stats = Counter()
    type_stats = defaultdict(lambda: {"total": 0, "accepted": 0})

    for item in tqdm(roots_data, desc="معالجة"):
        root = item["root"]
        result = handler.resolve(root)

        # تصنيف
        category = classify_result(result)
        source_stats[result.get("source", "?")] += 1

        # جمع المعلومات
        entry = {
            "root_camel": root,
            "root_suggested": result.get("root", root),
            "letter": result.get("letter", ""),
            "type": result.get("type", "?"),
            "confidence": result.get("confidence", 0.0),
            "source": result.get("source", "?"),
            "derivative_count": item["count"],
            "sample_words": ", ".join(item["samples"]),
            "category": category,
            "meaning_hint": result.get("meaning", ""),
        }

        all_results.append(entry)
        stats[category].append(entry)

        # إحصاء حسب النوع
        root_type = result.get("type", "غير معروف")
        type_stats[root_type]["total"] += 1
        if category == "accepted":
            type_stats[root_type]["accepted"] += 1

    # 3. كتابة الملفّات
    print(f"\n[3/4] كتابة الملفّات...")

    # الملفّ 1: كل النتائج (مرجعي شامل)
    all_file = OUTPUT_DIR / "resolved_roots.tsv"
    with open(all_file, 'w', encoding='utf-8-sig') as f:  # utf-8-sig للـ Excel
        f.write("root_camel\troot_suggested\tletter\ttype\t"
                "confidence\tsource\tcategory\tderivative_count\t"
                "sample_words\tmeaning_hint\tmanual_correction\n")
        for e in all_results:
            f.write(f"{e['root_camel']}\t{e['root_suggested']}\t{e['letter']}\t"
                    f"{e['type']}\t{e['confidence']:.2f}\t{e['source']}\t"
                    f"{e['category']}\t{e['derivative_count']}\t"
                    f"{e['sample_words']}\t{e['meaning_hint']}\t\n")
    print(f"      ✓ resolved_roots.tsv        : {len(all_results):,} جذر")

    # الملفّ 2: مراجعة يدوية (المشكوك فقط) — مرتّبة حسب الأهمّية
    manual_file = OUTPUT_DIR / "manual_review.tsv"
    manual_items = stats["suggested"] + stats["manual_required"]
    manual_items.sort(key=lambda x: -x["derivative_count"])  # الأهمّ أوّلاً

    with open(manual_file, 'w', encoding='utf-8-sig') as f:
        f.write("# ملفّ المراجعة اليدوية\n")
        f.write("# التعليمات:\n")
        f.write("# 1. افتح هذا الملفّ في Excel\n")
        f.write("# 2. راجع 'root_suggested' — هل صحيح؟\n")
        f.write("# 3. إذا خطأ، اكتب الجذر الصحيح في عمود 'manual_correction'\n")
        f.write("# 4. مثال: لو النظام يقترح 'ك.و.ن' وأنت متأكّد أنّه صحيح، اترك manual_correction فارغًا\n")
        f.write("# 5. لو النظام يقترح خطأ، اكتب الجذر الصحيح مثل 'ك.ي.ن'\n")
        f.write("# 6. رمز الرفض: اكتب 'SKIP' لتجاهل الجذر تمامًا\n\n")

        f.write("priority\troot_camel\troot_suggested\tconfidence\tsource\t"
                "type\tderivative_count\tsample_words\tmanual_correction\n")

        for i, e in enumerate(manual_items, 1):
            priority = "🔴 HIGH" if e["category"] == "manual_required" else "⚠️ MED"
            f.write(f"{priority}\t{e['root_camel']}\t{e['root_suggested']}\t"
                    f"{e['confidence']:.2f}\t{e['source']}\t{e['type']}\t"
                    f"{e['derivative_count']}\t{e['sample_words']}\t\n")
    print(f"      ✓ manual_review.tsv         : {len(manual_items):,} جذر للمراجعة")

    # الملفّ 3: التقرير الإحصائي
    stats_file = OUTPUT_DIR / "resolution_stats.txt"
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("تقرير معالجة الجذور الجوف\n")
        f.write("=" * 60 + "\n\n")

        total = len(all_results)
        f.write(f"إجمالي الجذور المعالَجة: {total:,}\n")
        f.write(f"إجمالي المشتقّات المتأثّرة: {total_derivatives:,}\n\n")

        f.write("─" * 60 + "\n")
        f.write("التوزيع حسب فئة الثقة:\n")
        f.write("─" * 60 + "\n")
        f.write(f"  ✅ مقبول تلقائيًا:      {len(stats['accepted']):>5,} ({100*len(stats['accepted'])/total:.1f}%)\n")
        f.write(f"  ⚠️  اقتراح للمراجعة:    {len(stats['suggested']):>5,} ({100*len(stats['suggested'])/total:.1f}%)\n")
        f.write(f"  🔴 مراجعة إلزامية:      {len(stats['manual_required']):>5,} ({100*len(stats['manual_required'])/total:.1f}%)\n\n")

        f.write("─" * 60 + "\n")
        f.write("التوزيع حسب المستوى (Level):\n")
        f.write("─" * 60 + "\n")
        for source, count in source_stats.most_common():
            f.write(f"  {source:20s} → {count:>5,} جذر\n")

        f.write("\n" + "─" * 60 + "\n")
        f.write("التوزيع حسب نوع الجذر (أجوف/مثال/ناقص/لفيف):\n")
        f.write("─" * 60 + "\n")
        for t, s in sorted(type_stats.items(), key=lambda x: -x[1]["total"]):
            acc_pct = 100 * s["accepted"] / s["total"] if s["total"] > 0 else 0
            f.write(f"  {t:20s}: {s['total']:>5,} إجمالي "
                    f"(مقبول: {s['accepted']:>4,} = {acc_pct:.0f}%)\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("سير العمل القادم:\n")
        f.write("=" * 60 + "\n")
        f.write("1. افتح manual_review.tsv في Excel أو محرّر نصوص\n")
        f.write("2. راجع الاقتراحات (الأعلى مشتقّات = الأهمّ)\n")
        f.write("3. صحّح الأخطاء في عمود 'manual_correction'\n")
        f.write("4. احفظ الملفّ (بنفس التنسيق TSV/UTF-8)\n")
        f.write("5. شغّل: python lexicon/apply_manual_review.py\n")

    print(f"      ✓ resolution_stats.txt      : تقرير إحصائي\n")

    # 4. الملخّص للمستخدم
    print(f"[4/4] الملخّص النهائي:")
    print(f"      " + "─" * 60)
    print(f"      ✅ مقبول تلقائيًا:  {len(stats['accepted']):>5,} ({100*len(stats['accepted'])/total:.1f}%)")
    print(f"      ⚠️  للمراجعة:        {len(stats['suggested']):>5,} ({100*len(stats['suggested'])/total:.1f}%)")
    print(f"      🔴 إلزامية:          {len(stats['manual_required']):>5,} ({100*len(stats['manual_required'])/total:.1f}%)")
    print(f"      " + "─" * 60)

    print(f"\n" + "=" * 70)
    print(f"✅ اكتملت المعالجة!")
    print(f"=" * 70)
    print(f"\nالخطوة التالية:")
    print(f"  1. افتح: lexicon\\manual_review.tsv (بـ Excel)")
    print(f"  2. راجع الاقتراحات وصحّح الأخطاء")
    print(f"  3. احفظ الملفّ")
    print(f"  4. سأُعطيك سكربت التطبيق (apply_manual_review.py) عند العودة")


if __name__ == "__main__":
    main()
