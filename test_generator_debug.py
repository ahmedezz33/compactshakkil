"""تشخيص مشاكل المولّد — نجرّب صيغًا متعدّدة."""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.generator import Generator
from camel_tools.morphology.analyzer import Analyzer

# ملاحظة: قد نحتاج db مختلف للتوليد
try:
    db_gen = MorphologyDB.builtin_db(flags="g")   # generate only
    generator = Generator(db_gen)
    print(f"تحميل قاعدة التوليد: OK")
except Exception as e:
    print(f"خطأ في تحميل قاعدة التوليد: {e}")
    print("نجرّب flags='ag' بدلاً منها")
    db_gen = MorphologyDB.builtin_db(flags="ag")
    generator = Generator(db_gen)

db_ana = MorphologyDB.builtin_db(flags="a")
analyzer = Analyzer(db_ana)

# نحصل على اللَّمّة المشكَّلة من التحليل
word = "قال"
analyses = analyzer.analyze(word)
if analyses:
    a = analyses[0]
    lemma_diac = a.get("diac")
    lemma_lex = a.get("lex")
    print(f"\nالكلمة: {word}")
    print(f"  diac:  {lemma_diac}")
    print(f"  lex:   {lemma_lex}")
    
    # نجرّب عدّة صيغ للـ features
    feature_variants = [
        {"pos": "verb", "asp": "i", "per": "3", "gen": "m", "num": "s", "mod": "i", "vox": "a"},
        {"pos": "verb", "asp": "i", "per": "3", "gen": "m", "num": "s"},
        {"pos": "verb", "asp": "i"},
    ]
    
    # نجرّب اللَّمّة بصيغتين (مشكَّلة وغير مشكَّلة)
    for lemma_try in [lemma_diac, lemma_lex]:
        print(f"\n  محاولة توليد من: {lemma_try}")
        for i, feats in enumerate(feature_variants):
            try:
                generated = generator.generate(lemma_try, feats)
                print(f"    [{i+1}] features={list(feats.keys())} → {len(generated)} صيغة")
                for g in generated[:2]:
                    print(f"         diac: {g.get('diac', '?')}, pattern: {g.get('pattern', '?')}")
            except Exception as e:
                print(f"    [{i+1}] خطأ: {e}")
