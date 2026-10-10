"""استعلامات متقدّمة على المعجم مع البحث الصحيح."""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path("lexicon/arabic_lexicon.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("═" * 60)
print("🔍 استعلامات متقدّمة")
print("═" * 60)

# 1. الجذور الحقيقية الأكثر تكرارًا (نستبعد الجذور المبهمة)
print("\n📊 أشهر 20 جذرًا حقيقيًا (بدون رموز #):")
print("─" * 60)
c.execute("""
    SELECT root, COUNT(*) as count 
    FROM roots 
    WHERE root NOT LIKE '%#%'
    GROUP BY root 
    ORDER BY count DESC 
    LIMIT 20
""")
for root, count in c.fetchall():
    print(f"   {root:15s} → {count:>6,} كلمة مشتقّة")

# 2. البحث عن مشتقّات جذر معيّن (بالعربية!)
target_roots = ["ك.ت.ب", "ع.ل.م", "ق.و.ل", "ف.ع.ل", "ح.م.د"]

for target_root in target_roots:
    print(f"\n📖 مشتقّات جذر '{target_root}':")
    print("─" * 60)
    c.execute("""
        SELECT w.word, w.frequency 
        FROM words w
        JOIN roots r ON w.id = r.word_id
        WHERE r.root = ?
        ORDER BY w.frequency DESC 
        LIMIT 10
    """, (target_root,))
    results = c.fetchall()
    if results:
        for word, freq in results:
            print(f"   {word:20s} → {freq:>8,}")
    else:
        print(f"   لا نتائج")

# 3. الفئات النحوية (توزيع صحيح)
print(f"\n📚 توزيع الفئات النحوية:")
print("─" * 60)
c.execute("""
    SELECT pos, COUNT(*) as count 
    FROM pos_tags 
    GROUP BY pos 
    ORDER BY count DESC
""")
for pos, count in c.fetchall():
    print(f"   {pos:15s} → {count:>8,}")

# 4. أطول كلمة في المعجم
print(f"\n📏 أطول 10 كلمات:")
print("─" * 60)
c.execute("SELECT word, frequency FROM words ORDER BY LENGTH(word) DESC LIMIT 10")
for word, freq in c.fetchall():
    print(f"   {word:30s} ({len(word)} حرف) → {freq:,}")

# 5. كلمات نادرة (مرّة واحدة فقط)
c.execute("SELECT COUNT(*) FROM words WHERE frequency = 1")
rare_count = c.fetchone()[0]
print(f"\n🔍 كلمات وردت مرّة واحدة فقط: {rare_count:,}")

# 6. عدد الكلمات لكل حرف بداية
print(f"\n📈 توزيع الكلمات حسب الحرف الأوّل:")
print("─" * 60)
c.execute("""
    SELECT SUBSTR(word, 1, 1) as first_char, COUNT(*) as count
    FROM words
    GROUP BY first_char
    ORDER BY count DESC
    LIMIT 15
""")
for char, count in c.fetchall():
    bar = "█" * (count // 500)
    print(f"   {char}  {count:>6,}  {bar}")

conn.close()
print("\n" + "═" * 60)
print("✅ اكتمل!")
print("═" * 60)