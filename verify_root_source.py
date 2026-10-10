# -*- coding: utf-8 -*-
"""
verify_root_source.py
تشخيص: هل حقل root من CAMeL يكفي وحده لتمييز الأصل الواويّ/اليائيّ
في الأفعال الجوف؟ يقارن 3 طرق على 13 فعلاً بأصولها المعروفة.

التشغيل:  python verify_root_source.py
"""
import sys, io

# فرض ترميز UTF-8 على المخرجات (حلّ انهيار cp1252 على ويندوز مع العربية)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.morphology.analyzer import Analyzer
    from camel_tools.morphology.generator import Generator
except Exception as e:
    print("خطأ في استيراد CAMeL Tools:", e)
    sys.exit(1)

# (الفعل الماضي, الأصل الحقيقيّ للحرف الأوسط: 'و' أو 'ي', الجذر الكامل المعروف)
VERBS = [
    ("قال", "و", "ق.و.ل"),
    ("باع", "ي", "ب.ي.ع"),
    ("صام", "و", "ص.و.م"),
    ("طال", "و", "ط.و.ل"),
    ("دار", "و", "د.و.ر"),
    ("كان", "و", "ك.و.ن"),
    ("زاد", "ي", "ز.ي.د"),
    ("خاف", "و", "خ.و.ف"),   # فَعِلَ واويّ — كان يفشل
    ("نام", "و", "ن.و.م"),   # فَعِلَ واويّ — كان يفشل
    ("مات", "و", "م.و.ت"),
    ("طاب", "ي", "ط.ي.ب"),
    ("هاب", "ي", "ه.ي.ب"),
    ("سار", "ي", "س.ي.ر"),   # كان يُحلَّل مضعّفًا (س.ر.ر)
]

WAW, YA = "و", "ي"  # و ، ي

def load():
    db_a = MorphologyDB.builtin_db(flags="a")
    db_g = MorphologyDB.builtin_db(flags="g")
    return Analyzer(db_a), Generator(db_g)

def verb_analyses(analyzer, word):
    out = []
    for a in analyzer.analyze(word):
        if a.get("pos") == "verb":
            out.append(a)
    return out

def middle_radical(root):
    """يستخرج الحرف الأوسط من جذر مثل 'ق.و.ل' أو 'قول'."""
    if not root:
        return None
    parts = root.split(".") if "." in root else list(root)
    parts = [p for p in parts if p.strip()]
    if len(parts) != 3:
        return None
    return parts[1]

def method_root(analyzer, word):
    """الطريقة A: من حقل root مباشرة. يجمع كل الجذور المميّزة من تحليلات الفعل."""
    roots = {}
    for a in verb_analyses(analyzer, word):
        r = a.get("root", "")
        roots[r] = roots.get(r, 0) + 1
    # اختر الجذر الأجوف (وسطه و/ي) الأكثر تكرارًا
    best = None
    for r, c in sorted(roots.items(), key=lambda x: -x[1]):
        m = middle_radical(r)
        if m in (WAW, YA):
            best = (r, m, c)
            break
    return roots, best

def method_present(generator, word):
    """الطريقة B: توليد المضارع (asp='i') وفحص و/ي في الصيغ."""
    try:
        gens = generator.generate(word, {"pos": "verb", "asp": "i"})
    except Exception as e:
        return f"gen_error: {e}", None
    forms = sorted({g.get("diac", "") for g in gens})
    has_waw = any(WAW in f for f in forms)
    has_ya = any(YA in f for f in forms)
    if has_waw and not has_ya:
        return forms, WAW
    if has_ya and not has_waw:
        return forms, YA
    return forms, None  # غامض

def dump_full_data(analyzer, generator):
    """المرحلة الثانية: استخراج كامل البيانات التي تعطيها CAMeL لكل فعل."""
    print("=" * 78)
    print("الجزء 1: استخراج كامل حقول CAMeL Tools (كل التحليلات)")
    print("=" * 78)

    all_keys = set()
    for word, truth, known_root in VERBS:
        analyses = analyzer.analyze(word)
        verb_an = [a for a in analyses if a.get("pos") == "verb"]
        print("\n" + "#" * 74)
        print(f"# الفعل: {word}   (الأصل: {truth} — {known_root})")
        print(f"# إجمالي التحليلات: {len(analyses)} | تحليلات الفعل: {len(verb_an)}")
        print("#" * 74)
        for i, a in enumerate(verb_an, 1):
            all_keys.update(a.keys())
            print(f"\n  ── تحليل الفعل رقم {i} ──")
            for k in sorted(a.keys()):
                print(f"     {k:<12}= {a[k]}")
        # توليد كل الصيغ (تحليل ما يعطيه Generator)
        try:
            gi = generator.generate(word, {"pos": "verb", "asp": "i"})   # مضارع
            gp = generator.generate(word, {"pos": "verb", "asp": "p"})   # ماضٍ
            print(f"\n  ── صيغ المضارع (asp=i): {len(gi)} صيغة ──")
            print("     ", sorted({g.get('diac','') for g in gi}))
            print(f"  ── صيغ الماضي (asp=p): {len(gp)} صيغة ──")
            print("     ", sorted({g.get('diac','') for g in gp}))
        except Exception as e:
            print("   تعذّر التوليد:", e)

    print("\n" + "=" * 78)
    print(f"كل الحقول المتاحة في تحليل الفعل ({len(all_keys)} حقلاً):")
    print("=" * 78)
    print("  " + ", ".join(sorted(all_keys)))


def main():
    analyzer, generator = load()

    # الجزء 1: كامل البيانات
    dump_full_data(analyzer, generator)

    # الجزء 2: التحقّق من المصدر
    print("\n\n" + "=" * 78)
    print("الجزء 2: تشخيص مصدر الأصل الواويّ/اليائيّ (3 طرق)")
    print("=" * 78)

    scoreA = scoreB = 0
    n = len(VERBS)
    rows = []
    for word, truth, known_root in VERBS:
        roots, best = method_root(analyzer, word)
        a_letter = best[1] if best else None
        a_root = best[0] if best else "—"
        forms, b_letter = method_present(generator, word)

        okA = "✅" if a_letter == truth else "❌"
        okB = "✅" if b_letter == truth else "❌"
        if a_letter == truth: scoreA += 1
        if b_letter == truth: scoreB += 1

        rows.append((word, truth, a_root, a_letter, okA, b_letter, okB))
        print(f"\n▌ {word}  (الأصل الصحيح: {truth} — {known_root})")
        print(f"   root من CAMeL (كل الجذور): {roots}")
        print(f"   [A] root  → أوسط={a_letter} ({a_root}) {okA}")
        print(f"   [B] مضارع → أوسط={b_letter} {okB}   الصيغ={forms if isinstance(forms,list) else forms}")

    print("\n" + "=" * 78)
    print("الملخّص")
    print("=" * 78)
    print(f"{'الفعل':<8}{'الأصل':<7}{'root→':<7}{'A':<4}{'مضارع→':<8}{'B':<4}")
    for word, truth, a_root, a_letter, okA, b_letter, okB in rows:
        print(f"{word:<8}{truth:<7}{str(a_letter):<7}{okA:<4}{str(b_letter):<8}{okB:<4}")
    print("-" * 40)
    print(f"دقّة الطريقة A (root):   {scoreA}/{n} = {100*scoreA//n}%")
    print(f"دقّة الطريقة B (مضارع): {scoreB}/{n} = {100*scoreB//n}%")

class _Tee:
    """يكتب المخرجات إلى الشاشة وإلى ملفّ UTF-8 معًا."""
    def __init__(self, *streams):
        self.streams = streams
    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except Exception:
                pass
    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass

if __name__ == "__main__":
    _f = open("jawf_output.txt", "w", encoding="utf-8")
    sys.stdout = _Tee(sys.stdout, _f)
    sys.stderr = sys.stdout
    try:
        main()
    finally:
        _f.flush()
        _f.close()
