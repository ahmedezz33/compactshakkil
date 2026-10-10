"""
بناء معجم عربي كامل من بيانات Tashkeela.

المخرجات:
    lexicon/arabic_lexicon.db  -  قاعدة بيانات SQLite
    lexicon/stats.txt          -  إحصاءات المعجم
"""

import sqlite3
import json
import re
from pathlib import Path
from collections import Counter
from tqdm import tqdm
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

# ═══════════════════════════════════════════════════════════
# الإعدادات
# ═══════════════════════════════════════════════════════════
INPUT_FILE = Path("data/raw/tashkeela/tashkeela_all.txt")
OUTPUT_DB = Path("lexicon/arabic_lexicon.db")
STATS_FILE = Path("lexicon/stats.txt")
MAX_WORDS = 200000   # حدّ أقصى للسرعة (يمكن رفعه لاحقًا)

# رموز الحركات لإزالتها عند الاستخراج
DIACRITICS = "\u064E\u0650\u064F\u0652\u064B\u064D\u064C\u0651"
ARABIC_LETTERS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوىيءأإآؤئة")


def strip_diacritics(text):
    """يزيل الحركات من النصّ."""
    return re.sub(f"[{DIACRITICS}]", "", text)


def is_valid_word(word):
    """يتحقّق أن الكلمة عربية صالحة."""
    stripped = strip_diacritics(word)
    if len(stripped) < 2 or len(stripped) > 20:
        return False
    return all(c in ARABIC_LETTERS for c in stripped)


def extract_unique_words(filepath, max_words=200000):
    """يستخرج الكلمات الفريدة من ملف Tashkeela."""
    print(f"📖 قراءة: {filepath}")
    word_counter = Counter()

    with open(filepath, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="استخراج الكلمات"):
            words = line.strip().split()
            for word in words:
                if is_valid_word(word):
                    # نحفظ الشكل غير المُشكَّل
                    stripped = strip_diacritics(word)
                    word_counter[stripped] += 1

    # نأخذ الأكثر شيوعًا
    most_common = word_counter.most_common(max_words)
    print(f"\n✅ الكلمات الفريدة: {len(word_counter):,}")
    print(f"   سنُحلّل أكثر {max_words:,} تكرارًا")
    return most_common


def analyze_and_store(words_with_counts, db_path):
    """يُحلّل الكلمات صرفيًا ويحفظها في SQLite."""
    print(f"\n🧠 تحميل CAMeL Tools...")
    db = MorphologyDB.builtin_db()
    analyzer = Analyzer(db)

    # إعداد قاعدة البيانات
    print(f"💾 إنشاء قاعدة البيانات: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # جدول الكلمات الرئيسية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            frequency INTEGER NOT NULL,
            num_analyses INTEGER NOT NULL,
            analyses_json TEXT NOT NULL
        )
    """)

    # جدول الجذور (للاستعلام السريع)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    """)

    # جدول اللواحق (الفئات النحوية)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pos_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pos TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    """)

    # فهارس للبحث السريع
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_word ON words(word)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_root ON roots(root)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pos ON pos_tags(pos)")

    # إحصاءات
    stats = {
        "total_words": 0,
        "analyzed": 0,
        "unanalyzed": 0,
        "root_counter": Counter(),
        "pos_counter": Counter(),
    }

    print(f"\n🔬 تحليل {len(words_with_counts):,} كلمة...")

    for word, freq in tqdm(words_with_counts, desc="تحليل صرفي"):
        try:
            analyses = analyzer.analyze(word)
            stats["total_words"] += 1

            if not analyses:
                stats["unanalyzed"] += 1
                continue

            stats["analyzed"] += 1

            # حفظ الكلمة الرئيسية
            analyses_data = []
            for a in analyses[:10]:  # أوّل 10 تحليلات (يكفي)
                analyses_data.append({
                    "diac": a.get("diac", ""),
                    "lex": a.get("lex", ""),
                    "root": a.get("root", ""),
                    "pos": a.get("pos", ""),
                    "pattern": a.get("pattern", ""),
                    "gloss": a.get("gloss", ""),
                    "gen": a.get("gen", ""),
                    "num": a.get("num", ""),
                })

            cursor.execute(
                "INSERT OR IGNORE INTO words (word, frequency, num_analyses, analyses_json) VALUES (?, ?, ?, ?)",
                (word, freq, len(analyses), json.dumps(analyses_data, ensure_ascii=False))
            )
            word_id = cursor.lastrowid

            # حفظ الجذور والفئات (لكل تحليل)
            roots_seen = set()
            pos_seen = set()
            for a in analyses:
                root = a.get("root", "")
                pos = a.get("pos", "")
                if root and root not in roots_seen:
                    roots_seen.add(root)
                    cursor.execute("INSERT INTO roots (root, word_id) VALUES (?, ?)",
                                   (root, word_id))
                    stats["root_counter"][root] += 1
                if pos and pos not in pos_seen:
                    pos_seen.add(pos)
                    cursor.execute("INSERT INTO pos_tags (pos, word_id) VALUES (?, ?)",
                                   (pos, word_id))
                    stats["pos_counter"][pos] += 1

        except Exception as e:
            stats["unanalyzed"] += 1
            continue

        # حفظ دوريّ كل 5000 كلمة
        if stats["total_words"] % 5000 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    return stats


def write_stats(stats, output_file):
    """يكتب إحصاءات المعجم."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("═" * 60 + "\n")
        f.write("إحصاءات المعجم العربي\n")
        f.write("═" * 60 + "\n\n")

        f.write(f"إجمالي الكلمات المُعالَجة:  {stats['total_words']:,}\n")
        f.write(f"الكلمات المُحلَّلة بنجاح:    {stats['analyzed']:,}\n")
        f.write(f"الكلمات غير المُحلَّلة:      {stats['unanalyzed']:,}\n")
        success_rate = stats['analyzed'] / max(1, stats['total_words']) * 100
        f.write(f"نسبة النجاح:                {success_rate:.1f}%\n\n")

        f.write(f"عدد الجذور الفريدة:        {len(stats['root_counter']):,}\n")
        f.write(f"عدد الفئات النحوية:        {len(stats['pos_counter']):,}\n\n")

        f.write("─" * 60 + "\n")
        f.write("أشهر 20 جذرًا:\n")
        f.write("─" * 60 + "\n")
        for root, count in stats['root_counter'].most_common(20):
            f.write(f"  {root:20s} → {count:,} كلمة\n")

        f.write("\n" + "─" * 60 + "\n")
        f.write("توزيع الفئات النحوية:\n")
        f.write("─" * 60 + "\n")
        for pos, count in stats['pos_counter'].most_common():
            f.write(f"  {pos:15s} → {count:,}\n")

        f.write("\n" + "═" * 60 + "\n")


def main():
    # تأكّد من المجلد
    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)

    # الخطوة 1: استخراج الكلمات
    words = extract_unique_words(INPUT_FILE, max_words=MAX_WORDS)

    # الخطوة 2: التحليل والحفظ
    stats = analyze_and_store(words, OUTPUT_DB)

    # الخطوة 3: الإحصاءات
    write_stats(stats, STATS_FILE)

    print(f"\n{'═' * 60}")
    print(f"✅ اكتمل بناء المعجم!")
    print(f"{'═' * 60}")
    print(f"   📁 قاعدة البيانات: {OUTPUT_DB.absolute()}")
    print(f"   📊 الإحصاءات: {STATS_FILE.absolute()}")
    print(f"   ✓ كلمات مُحلَّلة: {stats['analyzed']:,}")
    print(f"   ✓ جذور فريدة: {len(stats['root_counter']):,}")


if __name__ == "__main__":
    main()