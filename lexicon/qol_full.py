import sqlite3

conn = sqlite3.connect('lexicon/arabic_lexicon.db')
c = conn.cursor()

print("=" * 60)
print("كل مشتقات جذر قول (ق.#.ل)")
print("=" * 60)

c.execute("""
    SELECT w.word, w.frequency FROM words w
    JOIN roots r ON w.id = r.word_id
    WHERE r.root = 'ق.#.ل'
    ORDER BY w.frequency DESC
""")

results = c.fetchall()
print(f"\nإجمالي المشتقّات: {len(results):,}\n")

print("أشهر 30 مشتقّة:")
print("-" * 60)
for i, (word, freq) in enumerate(results[:30], 1):
    print(f"  {i:>3}. {word:20s} -> {freq:>10,}")

# إحصاءات
if results:
    total_freq = sum(f for _, f in results)
    print(f"\nإجمالي التكرارات: {total_freq:,}")
    print(f"متوسّط التكرار: {total_freq // len(results):,}")

print()
print("=" * 60)
print("مقارنة جذور الأفعال الجوفاء")
print("=" * 60)

hollow_roots = {
    "ق.#.ل": "قول",
    "ب.#.ع": "بيع",
    "س.#.ر": "سير",
    "ك.#.ن": "كون",
    "ق.#.م": "قوم",
    "ن.#.م": "نوم",
    "ص.#.م": "صوم",
    "ط.#.ب": "طيب",
}

for root, meaning in hollow_roots.items():
    c.execute("SELECT COUNT(*) FROM roots WHERE root = ?", (root,))
    count = c.fetchone()[0]
    if count > 0:
        print(f"  {root} ({meaning:8s}) -> {count:>4,} مشتقّة")

conn.close()