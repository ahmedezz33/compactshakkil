"""الخوارزمية الذهبية v3 — تحلّ فَعَلَ و فَعِلَ معًا."""
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.morphology.generator import Generator

print("Loading DBs...")
db_ana = MorphologyDB.builtin_db(flags="a")
db_gen = MorphologyDB.builtin_db(flags="g")
analyzer = Analyzer(db_ana)
generator = Generator(db_gen)
print("OK\n")

# أنماط وزن فَعَلَ (المضارع الرافع)
PATTERNS_WAW_PRESENT = {"يَ1ُو3", "تَ1ُو3", "أَ1ُو3", "نَ1ُو3"}
PATTERNS_YA_PRESENT  = {"يَ1ِي3", "تَ1ِي3", "أَ1ِي3", "نَ1ِي3"}

# أنماط وزن فَعِلَ (صيغة المتكلّم الماضية)
PATTERNS_WAW_PAST = {"1ُ3ْتُ", "1ُ3ُّ"}
PATTERNS_YA_PAST  = {"1ِ3ْتُ", "1ِ3ُّ"}


def resolve_hollow(word):
    """يحلّ فعلاً جوفًا بمنهج متعدّد المراحل."""
    
    # 1. تحليل
    analyses = analyzer.analyze(word)
    verbs = [a for a in analyses if a.get("pos") == "verb"]
    if not verbs:
        return None, "not_verb", 0.0, "-"
    
    a = verbs[0]
    root_ambig = a.get("root", "")
    lemma = a.get("lex", "")
    
    if "#" not in root_ambig:
        return root_ambig, "not_hollow", 1.0, "-"
    
    # 2. المرحلة الأولى — المضارع (وزن فَعَلَ)
    try:
        gen_present = generator.generate(lemma, {"pos": "verb", "asp": "i"})
    except:
        gen_present = []
    
    waw_p = sum(1 for g in gen_present if g.get("pattern") in PATTERNS_WAW_PRESENT)
    ya_p  = sum(1 for g in gen_present if g.get("pattern") in PATTERNS_YA_PRESENT)
    
    if waw_p + ya_p > 0:
        if waw_p > ya_p:
            return root_ambig.replace("#", "و"), "confirmed_waw", 1.0, "present_pattern"
        elif ya_p > waw_p:
            return root_ambig.replace("#", "ي"), "confirmed_ya", 1.0, "present_pattern"
    
    # 3. المرحلة الثانية — المتكلّم الماضي (وزن فَعِلَ)
    try:
        gen_past_1s = generator.generate(lemma, {
            "pos": "verb", "asp": "p", "per": "1", "gen": "m", "num": "s"
        })
    except:
        gen_past_1s = []
    
    waw_pt = sum(1 for g in gen_past_1s if g.get("pattern") in PATTERNS_WAW_PAST)
    ya_pt  = sum(1 for g in gen_past_1s if g.get("pattern") in PATTERNS_YA_PAST)
    
    if waw_pt + ya_pt > 0:
        if waw_pt > ya_pt:
            return root_ambig.replace("#", "و"), "confirmed_waw", 1.0, "past_1s_pattern"
        elif ya_pt > waw_pt:
            return root_ambig.replace("#", "ي"), "confirmed_ya", 1.0, "past_1s_pattern"
    
    # 4. لم نستطع الحسم
    return root_ambig, "needs_review", 0.0, "no_pattern"


# اختبار موسّع — الفئتان معًا
test_words = [
    # وزن فَعَلَ (رأينا نجاحًا سابقًا)
    ("قال", "و"),
    ("باع", "ي"),
    ("صام", "و"),
    ("طال", "و"),
    ("دار", "و"),
    ("كان", "و"),
    ("زاد", "ي"),
    # وزن فَعِلَ (الحالات الصعبة)
    ("خاف", "و"),
    ("نام", "و"),
    ("مات", "و"),
    ("طاب", "ي"),
    ("هاب", "ي"),
    ("سار", "ي"),
]

print("=" * 70)
print(f"{'الفعل':10} {'الحقيقيّ':10} {'الجذر':15} {'الحالة':20} {'المصدر':20}")
print("=" * 70)

correct = 0
total = 0
for word, true_letter in test_words:
    root, status, conf, source = resolve_hollow(word)
    resolved_letter = root.replace(".", "").replace(word[0], "").replace(word[-1], "")[:1] if root else "?"
    total += 1
    # فحص الصحّة
    got_letter = "و" if "confirmed_waw" in status else ("ي" if "confirmed_ya" in status else "?")
    mark = "✅" if got_letter == true_letter else "❌"
    if got_letter == true_letter:
        correct += 1
    print(f"{word:10} {true_letter:10} {str(root):15} {status:20} {source:20} {mark}")

print("=" * 70)
print(f"\nالدقّة: {correct}/{total} = {int(100*correct/total)}%")