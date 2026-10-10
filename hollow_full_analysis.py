"""فحص كامل — كل ما تعرفه CAMeL عن الأفعال الجوف من وزن فَعِلَ."""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.morphology.generator import Generator

db_ana = MorphologyDB.builtin_db(flags="a")
db_gen = MorphologyDB.builtin_db(flags="g")
analyzer = Analyzer(db_ana)
generator = Generator(db_gen)

# أفعال من وزن فَعِلَ (المشكلة)
words = {
    "خاف": "و",   # from خوف - الحرف الحقيقي
    "نام": "و",   # from نوم
    "هاب": "ي",   # from هيب
    "سار": "ي",   # from سير
    "طاب": "ي",   # from طيب
    "مات": "و",   # from موت
}

for word, true_letter in words.items():
    print("\n" + "=" * 70)
    print(f"الفعل: {word}   (الحرف الأصليّ الحقيقيّ: {true_letter})")
    print("=" * 70)
    
    # 1. كل التحليلات (لا الأوّل فقط)
    analyses = analyzer.analyze(word)
    verb_analyses = [a for a in analyses if a.get("pos") == "verb"]
    print(f"\nعدد التحليلات الفعلية: {len(verb_analyses)}")
    
    for i, a in enumerate(verb_analyses[:3]):
        print(f"\n--- التحليل {i+1} ---")
        # كل الحقول
        important = ["root", "lex", "diac", "stemcat", "pattern", "bw", 
                     "bwtok", "atbtok", "d3tok", "d3seg", "asp", "vox"]
        for key in important:
            if key in a:
                val = str(a[key])[:60]
                print(f"  {key:12}: {val}")
    
    # 2. توليد المصدر (verbal noun)
    lemma = verb_analyses[0].get("lex")
    print(f"\n--- توليد المصدر (masdar) ---")
    try:
        gen_noun = generator.generate(lemma, {"pos": "noun"})
        if gen_noun:
            print(f"  عدد صيغ الاسم: {len(gen_noun)}")
            for g in gen_noun[:5]:
                print(f"    diac: {g.get('diac', '?'):15} pattern: {g.get('pattern', '?')}")
        else:
            print("  لم يوّلد أسماء")
    except Exception as e:
        print(f"  خطأ: {e}")
    
    # 3. توليد صيغ المصدر بميزات أخرى
    print(f"\n--- محاولات توليد أخرى ---")
    variants = [
        {"pos": "verb", "asp": "c"},           # الأمر
        {"pos": "verb", "asp": "p", "per": "1", "gen": "m", "num": "s"},  # أنا فعلت
    ]
    for feats in variants:
        try:
            g = generator.generate(lemma, feats)
            if g:
                sample = g[0]
                print(f"  {feats} → {sample.get('diac', '?')} ({sample.get('pattern', '?')})")
        except:
            pass