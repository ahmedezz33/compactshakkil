import sqlite3
import json

conn = sqlite3.connect('lexicon/arabic_lexicon.db')
c = conn.cursor()

print("=" * 60)
print("البحث عن كل جذور الكلمات المرتبطة بـ قول")
print("=" * 60)

# ابحث عن كلمات مشتقّة من "قول"
words_to_check = ["قال", "قول", "يقول", "قائل", "مقال", "أقوال", "قالوا"]

for word in words_to_check:
    c.execute("SELECT analyses_json FROM words WHERE word = ?", (word,))
    result = c.fetchone()
    
    if result:
        analyses = json.loads(result[0])
        roots_found = set()
        for a in analyses:
            root = a.get('root', '')
            if root:
                roots_found.add(root)
        
        print(f"\nكلمة '{word}':")
        for root in roots_found:
            print(f"   الجذر: '{root}'")
    else:
        print(f"\nكلمة '{word}': غير موجودة في المعجم")

print()
print("=" * 60)
print("كل الجذور التي تحتوي 'ق' و 'ل'")
print("=" * 60)

c.execute("""
    SELECT DISTINCT root FROM roots 
    WHERE root LIKE 'ق%ل%' AND root NOT LIKE '%#%'
    LIMIT 30
""")

for row in c.fetchall():
    print(f"   {row[0]}")

conn.close()