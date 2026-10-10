"""نستكشف كل صيغ المضارع المولَّدة."""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.generator import Generator

db_gen = MorphologyDB.builtin_db(flags="g")
generator = Generator(db_gen)

# نستخدم اللَّمّة غير المشكَّلة (اكتشفنا أنّها تعمل)
words = ["قال", "باع", "صام"]

for word in words:
    print(f"\n{'=' * 70}")
    print(f"الفعل: {word}")
    print("=" * 70)
    
    # ميزات بسيطة (أقلّ = صيغ أكثر)
    feats = {"pos": "verb", "asp": "i"}
    
    generated = generator.generate(word, feats)
    print(f"إجمالي: {len(generated)} صيغة")
    
    # جميع الأنماط الفريدة
    patterns = {}
    for g in generated:
        p = g.get("pattern", "?")
        d = g.get("diac", "?")
        if p not in patterns:
            patterns[p] = []
        patterns[p].append(d)
    
    print(f"\nالأنماط الفريدة ({len(patterns)}):")
    for pattern, examples in patterns.items():
        # نأخذ أوّل مثال من كل نمط
        example = examples[0]
        count = len(examples)
        marker = ""
        # نُظهر الأنماط الحاسمة
        if "و" in pattern:
            marker = " ← نمط واويّ"
        elif "ي" in pattern:
            marker = " ← نمط يائيّ"
        print(f"  {pattern:12} → {example:12} ({count} تصريف){marker}")
