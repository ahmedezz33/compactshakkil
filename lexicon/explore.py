"""استكشاف تفاعلي للمعجم العربي."""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path("lexicon/arabic_lexicon.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("═" * 60)
print("🔍 استكشاف المعجم العربي")
print("═" * 60)

# 1. إحصاءات عامّة
cursor.execute("SELECT COUNT(*) FROM words")
total = cursor.fetchone()[0]
print(f"\n📊 إجمالي الكلمات في المعجم: {total:,}")

cursor.execute("SELECT COUNT(DISTINCT root) FROM roots")
roots_count = cursor.fetchone()[0]
print(f"🌱 عدد الجذور الفريدة: {roots_count:,}")

# 2. أشهر 15 كلمة
print("\n" + "─" * 60)
print("📈 أشهر 15 كلمة:")
print("─" * 60)
cursor.execute("SELECT word, frequency FROM words ORDER BY frequency DESC LIMIT 15")
for word, freq in cursor.fetchall():
    print(f"   {word:20s} → {freq:>10,} مرّة")

# 3. الكلمات المشتقّة من جذر "ك-ت-ب"
print("\n" + "─" * 60)
print("📖 الكلمات المشتقّة من جذر ك-ت-ب:")
print("─" * 60)
cursor.execute("""
    SELECT w.word, w.frequency FROM words w
    JOIN roots r ON w.id = r.word_id
    WHERE r.root = 'k.t.b'
    ORDER BY w.frequency DESC LIMIT 20
""")
results = cursor.fetchall()
if results:
    for word, freq in results:
        print(f"   {word:20s} → {freq:>10,}")
else:
    print("   لا توجد نتائج بهذا الجذر")

# 4. الكلمات المشتقّة من جذر "ع-ل-م"
print("\n" + "─" * 60)
print("🎓 الكلمات المشتقّة من جذر ع-ل-م:")
print("─" * 60)
cursor.execute("""
    SELECT w.word, w.frequency FROM words w
    JOIN roots r ON w.id = r.word_id
    WHERE r.root = 'E.l.m'
    ORDER BY w.frequency DESC LIMIT 20
""")
results = cursor.fetchall()
if results:
    for word, freq in results:
        print(f"   {word:20s} → {freq:>10,}")

# 5. تحليل كلمة معيّنة
print("\n" + "─" * 60)
print("🔬 تحليل كلمة 'كتاب':")
print("─" * 60)
cursor.execute("SELECT analyses_json FROM words WHERE word = 'كتاب'")
result = cursor.fetchone()
if result:
    analyses = json.loads(result[0])
    for i, a in enumerate(analyses[:5], 1):
        print(f"\n   التحليل {i}:")
        print(f"      الشكل المشكّل: {a['diac']}")
        print(f"      اللفظ المعجمي: {a['lex']}")
        print(f"      الجذر: {a['root']}")
        print(f"      الوزن: {a['pattern']}")
        print(f"      الفئة: {a['pos']}")

# 6. أشهر الأفعال
print("\n" + "─" * 60)
print("⚡ أشهر 15 فعلًا:")
print("─" * 60)
cursor.execute("""
    SELECT DISTINCT w.word, w.frequency FROM words w
    JOIN pos_tags p ON w.id = p.word_id
    WHERE p.pos = 'verb'
    ORDER BY w.frequency DESC LIMIT 15
""")
for word, freq in cursor.fetchall():
    print(f"   {word:20s} → {freq:>10,}")

# 7. أشهر الأسماء
print("\n" + "─" * 60)
print("📚 أشهر 15 اسمًا:")
print("─" * 60)
cursor.execute("""
    SELECT DISTINCT w.word, w.frequency FROM words w
    JOIN pos_tags p ON w.id = p.word_id
    WHERE p.pos = 'noun'
    ORDER BY w.frequency DESC LIMIT 15
""")
for word, freq in cursor.fetchall():
    print(f"   {word:20s} → {freq:>10,}")

conn.close()
print("\n" + "═" * 60)
print("✅ اكتمل الاستكشاف!")
print("═" * 60)