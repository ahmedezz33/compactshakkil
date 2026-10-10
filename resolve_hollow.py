"""الخوارزمية الذهبية — نسخة قوية مع معالجة الأخطاء."""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.morphology.generator import Generator

print("Loading DBs...")
db_ana = MorphologyDB.builtin_db(flags="a")
db_gen = MorphologyDB.builtin_db(flags="g")
analyzer = Analyzer(db_ana)
generator = Generator(db_gen)
print("OK\n")

PATTERNS_WAW = {"يَ1ُو3", "تَ1ُو3", "أَ1ُو3", "نَ1ُو3"}
PATTERNS_YA  = {"يَ1ِي3", "تَ1ِي3", "أَ1ِي3", "نَ1ِي3"}


def resolve_hollow(word):
    """يحلّ فعلاً جوفًا. يُرجع (root, status, confidence)."""
    try:
        analyses = analyzer.analyze(word)
    except Exception as e:
        return None, "analyze_error", 0.0

    if not analyses:
        return None, "no_analysis", 0.0

    verbs = [a for a in analyses if a.get("pos") == "verb"]
    if not verbs:
        return None, "not_verb", 0.0

    a = verbs[0]
    root_ambig = a.get("root", "")
    lemma = a.get("lex", "")

    if "#" not in root_ambig:
        return root_ambig, "not_hollow", 1.0

    try:
        generated = generator.generate(lemma, {"pos": "verb", "asp": "i"})
    except Exception as e:
        return root_ambig, "generate_error", 0.0

    if not generated:
        return root_ambig, "no_generation", 0.0

    waw_count = 0
    ya_count = 0
    for g in generated:
        p = g.get("pattern", "")
        if p in PATTERNS_WAW:
            waw_count += 1
        elif p in PATTERNS_YA:
            ya_count += 1

    total = waw_count + ya_count
    if total == 0:
        return root_ambig, "no_pattern_match", 0.0

    if waw_count > ya_count:
        conf = waw_count / total
        return root_ambig.replace("#", "و"), "confirmed_waw", conf
    elif ya_count > waw_count:
        conf = ya_count / total
        return root_ambig.replace("#", "ي"), "confirmed_ya", conf
    else:
        return root_ambig, "ambiguous", 0.5


test_words = ["قال", "باع", "صام", "زاد", "خاف", "طال", "دار", "كان"]

print("=" * 60)
print("Test Results")
print("=" * 60)

for word in test_words:
    root, status, conf = resolve_hollow(word)
    print("")
    print(word + ":")
    print("  root:   " + str(root))
    print("  status: " + status)
    print("  conf:   " + str(int(conf*100)) + "%")