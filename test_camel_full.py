"""ماذا يعرف CAMeL فعلًا عن الأفعال الجوف؟"""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

db = MorphologyDB.builtin_db()
analyzer = Analyzer(db)

words = ["قال", "باع", "صام"]

for w in words:
    print("=" * 60)
    print(f"الكلمة: {w}")
    print("=" * 60)
    
    analyses = analyzer.analyze(w)
    if not analyses:
        print("  لا يوجد تحليل")
        continue
    
    print(f"  عدد التحليلات: {len(analyses)}")
    
    # نطبع أوّل تحليلين بكل الحقول
    for i, a in enumerate(analyses[:2]):
        print(f"\n  --- التحليل {i+1} ---")
        for key in sorted(a.keys()):
            val = a[key]
            # نطبع فقط القيم القصيرة والمفهومة
            val_str = str(val)
            if len(val_str) < 40:
                print(f"    {key:15}: {val_str}")
    print()
