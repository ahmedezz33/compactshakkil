"""فحص: هل CAMeL يوّلد المضارع من الماضي؟"""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.generator import Generator
from camel_tools.morphology.analyzer import Analyzer

db = MorphologyDB.builtin_db(flags="ag")  # analyze + generate
analyzer = Analyzer(db)
generator = Generator(db)

words = ["قال", "باع", "صام", "زاد"]

for w in words:
    print(f"\n{'=' * 50}")
    print(f"الماضي: {w}")
    print("=" * 50)
    
    analyses = analyzer.analyze(w)
    verb_analyses = [a for a in analyses if a.get("pos") == "verb"]
    
    if not verb_analyses:
        print(f"  لا توجد تحليلات فعليّة")
        continue
    
    print(f"  تحليلات فعليّة: {len(verb_analyses)}")
    a = verb_analyses[0]
    lemma = a.get("lex")
    print(f"  اللَّمّة: {lemma}")
    
    # نطلب توليد المضارع (asp=i = imperfect)
    features = {
        "pos": "verb",
        "asp": "i",           # مضارع
        "per": "3",           # الغائب
        "gen": "m",           # مذكّر
        "num": "s",           # مفرد
        "mod": "i",           # indicative
    }
    
    try:
        generated = generator.generate(lemma, features)
        print(f"  المضارع المولَّد: {len(generated)} صيغة")
        for i, g in enumerate(generated[:3]):
            print(f"    [{i+1}] diac: {g.get('diac', '?')}, pattern: {g.get('pattern', '?')}")
    except Exception as e:
        print(f"  خطأ في التوليد: {e}")
