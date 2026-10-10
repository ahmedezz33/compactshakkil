import sqlite3

conn = sqlite3.connect('lexicon/arabic_lexicon.db')
c = conn.cursor()

roots = ["ف.ع.ل", "ك.ت.ب", "ع.ل.م", "ق.و.ل", "ح.م.د", "ن.ظ.ر", "ذ.ك.ر", "س.م.ع"]

print("=" * 50)
print("عدد المشتقّات لكل جذر")
print("=" * 50)

for root in roots:
    c.execute("SELECT COUNT(*) FROM roots WHERE root = ?", (root,))
    count = c.fetchone()[0]
    print(f"  {root} -> {count:,} مشتقّة")

print()
print("=" * 50)
print("أعلى 20 جذرا من حيث عدد المشتقات")
print("=" * 50)

query = "SELECT root, COUNT(*) FROM roots WHERE root NOT LIKE '%#%' GROUP BY root ORDER BY COUNT(*) DESC LIMIT 20"
c.execute(query)

for i, row in enumerate(c.fetchall(), 1):
    root = row[0]
    count = row[1]
    print(f"  {i}. {root} -> {count:,}")

conn.close()