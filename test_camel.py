from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

db = MorphologyDB.builtin_db()
analyzer = Analyzer(db)

words = ["قال", "كتب", "باع", "يذهب", "المكتبة", "صام", "طال", "خاف"]

for w in words:
    analyses = analyzer.analyze(w)
    print(f"=== {w} ===")
    if not analyses:
        print("  لا يوجد تحليل")
        print()
        continue
    a = analyses[0]
    root = a.get("root", "?")
    lex = a.get("lex", "?")
    pos = a.get("pos", "?")
    diac = a.get("diac", "?")
    pattern = a.get("pattern", "?")
    print(f"  Root:    {root}")
    print(f"  Lemma:   {lex}")
    print(f"  POS:     {pos}")
    print(f"  Diac:    {diac}")
    print(f"  Pattern: {pattern}")
    print(f"  Total analyses: {len(analyses)}")
    print()
