"""
استخراج كل الجذور الجوف من المعجم.
الجذور الجوف = الجذور التي تحوي رمز # (حرف علة محذوف)
"""

import sqlite3
import json
from collections import defaultdict

conn = sqlite3.connect('lexicon/arabic_lexicon.db')
c = conn.cursor()

print("=" * 60)
print("استخراج الجذور الجوف من المعجم")
print("=" * 60)

# 1. عدّ الجذور الجوف
c.execute("SELECT COUNT(DISTINCT root) FROM roots WHERE root LIKE '%#%'")
total_hollow = c.fetchone()[0]
print(f"\nإجمالي الجذور الجوف الفريدة: {total_hollow:,}")

# 2. عدّ الجذور غير الجوف (للمقارنة)
c.execute("SELECT COUNT(DISTINCT root) FROM roots WHERE root NOT LIKE '%#%'")
total_clean = c.fetchone()[0]
print(f"إجمالي الجذور الصحيحة: {total_clean:,}")

if total_hollow + total_clean > 0:
    pct = 100 * total_hollow / (total_hollow + total_clean)
    print(f"نسبة الجذور الجوف: {pct:.1f}%")

# 3. تصنيف الجذور الجوف حسب موقع الحرف المعتلّ
print()
print("=" * 60)
print("تصنيف الجذور الجوف حسب موقع الحرف المعتلّ")
print("=" * 60)

categories = {
    "أجوف (وسط)": 0,      # ق.#.ل
    "مثال (بداية)": 0,     # #.ع.د
    "ناقص (آخر)": 0,       # ر.م.#
    "لفيف مقرون": 0,       # #.#.ل
    "لفيف مفروق": 0,       # #.ع.#
    "غير محدّد": 0,
}

examples_by_category = defaultdict(list)

c.execute("SELECT DISTINCT root FROM roots WHERE root LIKE '%#%'")
all_hollow_roots = [row[0] for row in c.fetchall()]

for root in all_hollow_roots:
    parts = root.split('.')
    if len(parts) == 3:
        first, middle, last = parts
        first_hash = (first == '#')
        middle_hash = (middle == '#')
        last_hash = (last == '#')
        
        num_hash = sum([first_hash, middle_hash, last_hash])
        
        if num_hash == 1:
            if middle_hash:
                categories["أجوف (وسط)"] += 1
                if len(examples_by_category["أجوف (وسط)"]) < 5:
                    examples_by_category["أجوف (وسط)"].append(root)
            elif first_hash:
                categories["مثال (بداية)"] += 1
                if len(examples_by_category["مثال (بداية)"]) < 5:
                    examples_by_category["مثال (بداية)"].append(root)
            elif last_hash:
                categories["ناقص (آخر)"] += 1
                if len(examples_by_category["ناقص (آخر)"]) < 5:
                    examples_by_category["ناقص (آخر)"].append(root)
        elif num_hash == 2:
            if first_hash and middle_hash:
                categories["لفيف مقرون"] += 1
                if len(examples_by_category["لفيف مقرون"]) < 5:
                    examples_by_category["لفيف مقرون"].append(root)
            elif first_hash and last_hash:
                categories["لفيف مفروق"] += 1
                if len(examples_by_category["لفيف مفروق"]) < 5:
                    examples_by_category["لفيف مفروق"].append(root)
            elif middle_hash and last_hash:
                categories["لفيف مقرون"] += 1
                if len(examples_by_category["لفيف مقرون"]) < 5:
                    examples_by_category["لفيف مقرون"].append(root)
        else:
            categories["غير محدّد"] += 1
    else:
        categories["غير محدّد"] += 1

# طباعة الإحصاءات
print()
for cat, count in categories.items():
    if count > 0:
        print(f"  {cat:20s} -> {count:>5,} جذر")
        for ex in examples_by_category[cat][:3]:
            print(f"     مثال: {ex}")

# 4. أعلى 20 جذرًا جوفًا من حيث الإنتاجية
print()
print("=" * 60)
print("أعلى 20 جذرًا جوفًا من حيث عدد المشتقّات")
print("=" * 60)

query = """
    SELECT root, COUNT(*) as count 
    FROM roots 
    WHERE root LIKE '%#%'
    GROUP BY root 
    ORDER BY count DESC 
    LIMIT 20
"""
c.execute(query)

top_hollow = c.fetchall()
print()
for i, (root, count) in enumerate(top_hollow, 1):
    print(f"  {i:>2}. {root:12s} -> {count:>5,} مشتقّة")

# 5. حفظ قائمة الجذور الجوف الأكثر إنتاجية للمعالجة اللاحقة
output_file = "lexicon/hollow_roots.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# قائمة الجذور الجوف مرتّبة حسب عدد المشتقّات\n")
    f.write("# التنسيق: الجذر<TAB>عدد المشتقّات\n\n")
    
    c.execute("""
        SELECT root, COUNT(*) as count 
        FROM roots 
        WHERE root LIKE '%#%'
        GROUP BY root 
        ORDER BY count DESC
    """)
    for root, count in c.fetchall():
        f.write(f"{root}\t{count}\n")

print()
print(f"تمّ حفظ قائمة الجذور الجوف في: {output_file}")

conn.close()
print()
print("=" * 60)
print("اكتمل!")
print("=" * 60)