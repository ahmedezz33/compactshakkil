"""فحص فرضية: هل CAMeL يميّز الأصل عبر المضارع؟"""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

db = MorphologyDB.builtin_db()
analyzer = Analyzer(db)

# أزواج (فعل ماضٍ جوف → مضارعه)
pairs = [
    ("قال", "يقول"),   # واويّ
    ("باع", "يبيع"),   # يائيّ
    ("صام", "يصوم"),   # واويّ
    ("زاد", "يزيد"),   # يائيّ
    ("خاف", "يخاف"),   # واويّ (مثال شاذّ)
]

for past, present in pairs:
    print(f"\n{'=' * 60}")
    print(f"الماضي: {past}   المضارع: {present}")
    print("=" * 60)
    
    for word, label in [(past, "ماضٍ"), (present, "مضارع")]:
        analyses = analyzer.analyze(word)
        if not analyses:
            print(f"  [{label}] {word}: لا تحليل")
            continue
        a = analyses[0]
        print(f"  [{label}] {word}:")
        print(f"       root:     {a.get('root', '?')}")
        print(f"       diac:     {a.get('diac', '?')}")
        print(f"       stemcat:  {a.get('stemcat', '?')}")
        print(f"       pattern:  {a.get('pattern', '?')}")
        print(f"       bw:       {a.get('bw', '?')[:50]}")
