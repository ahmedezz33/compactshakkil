"""استكشاف شامل لكل قدرات CAMeL على فعل جوف من وزن فَعِلَ."""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.morphology.generator import Generator

WORD = "خاف"

print("=" * 70)
print(f"استكشاف شامل: {WORD}")
print("=" * 70)

# 1. Analyzer مع كل الـ backoff
print("\n[1] Analyzer مع backoff مختلفة")
print("-" * 50)
db = MorphologyDB.builtin_db()

for backoff in ["NONE", "NOAN_ALL", "NOAN_PROP", "ADD_ALL", "ADD_PROP"]:
    try:
        a = Analyzer(db, backoff=backoff)
        results = a.analyze(WORD)
        print(f"backoff={backoff}: {len(results)} تحليل")
    except Exception as e:
        print(f"backoff={backoff}: خطأ - {str(e)[:40]}")

# 2. كل الحقول لأوّل تحليل فعليّ
print("\n[2] كل حقول التحليل الأوّل")
print("-" * 50)
a = Analyzer(db)
analyses = a.analyze(WORD)
verbs = [x for x in analyses if x.get("pos") == "verb"]
if verbs:
    for key in sorted(verbs[0].keys()):
        val = str(verbs[0][key])[:70]
        print(f"  {key:15} = {val}")

# 3. Reinflector - قد يعطي معلومات أكثر
print("\n[3] Reinflector (جديد!)")
print("-" * 50)
try:
    from camel_tools.morphology.reinflector import Reinflector
    db_r = MorphologyDB.builtin_db(flags="r")
    reinflector = Reinflector(db_r)
    
    variants = [
        {"asp": "i", "per": "3", "gen": "m", "num": "s"},
        {"asp": "i", "per": "1", "gen": "m", "num": "s"},
        {"asp": "c", "per": "2", "gen": "m", "num": "s"},
    ]
    for v in variants:
        try:
            results = reinflector.reinflect(WORD, v)
            print(f"features={list(v.keys())}: {len(results)} نتيجة")
            for r in results[:2]:
                print(f"    diac: {r.get('diac', '?'):15} pattern: {r.get('pattern', '?')}")
        except Exception as e:
            print(f"features={v}: خطأ - {str(e)[:50]}")
except ImportError:
    print("Reinflector غير متاح في هذا الإصدار")
except Exception as e:
    print(f"خطأ عامّ: {e}")

# 4. Disambiguator (اختيار أفضل تحليل)
print("\n[4] Disambiguator")
print("-" * 50)
try:
    from camel_tools.disambig.mle import MLEDisambiguator
    mle = MLEDisambiguator.pretrained()
    disambig = mle.disambiguate([WORD])
    if disambig:
        best = disambig[0].analyses[0]
        if hasattr(best, "analysis"):
            print(f"أفضل تحليل: {best.analysis.get('lex', '?')} - root: {best.analysis.get('root', '?')}")
except Exception as e:
    print(f"خطأ: {str(e)[:80]}")

# 5. Tokenizer الصرفيّ
print("\n[5] Morphological Tokenizer")
print("-" * 50)
try:
    from camel_tools.tokenizers.morphological import MorphologicalTokenizer
    tok = MorphologicalTokenizer.pretrained()
    tokens = tok.tokenize([WORD])
    print(f"tokens: {tokens}")
except Exception as e:
    print(f"خطأ: {str(e)[:80]}")

# 6. المصدر - محاولات متعدّدة
print("\n[6] توليد المصدر (verbal noun)")
print("-" * 50)
db_g = MorphologyDB.builtin_db(flags="g")
gen = Generator(db_g)

lemma = verbs[0].get("lex") if verbs else WORD
print(f"اللَّمّة: {lemma}")

masdar_features = [
    {"pos": "noun"},
    {"pos": "noun", "form_gen": "m"},
    {"pos": "noun", "form_num": "s"},
]

for feats in masdar_features:
    try:
        results = gen.generate(lemma, feats)
        if results:
            unique_diacs = set(r.get("diac", "") for r in results)
            print(f"  {feats} → {len(unique_diacs)} صيغة فريدة")
            for d in list(unique_diacs)[:5]:
                print(f"      {d}")
    except Exception as e:
        print(f"  {feats} → خطأ")