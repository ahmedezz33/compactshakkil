# -*- coding: utf-8 -*-
"""
dagger_lexicon.py — طبقة رمزيّة مغلقة للألف الخنجريّة (ٰ).

الخنجريّة تقع على قائمة شبه مغلقة من كلمات مبنيّة/مقصورة ثابتة الصورة، فالمعجم
يحسمها بيقين بعد مخرَج النموذج العصبيّ. القرآن يتكفّل به V3 (استرداد الأصل)،
وفي الكلام الطبيعيّ الخنجريّة نادرة ومحصورة — فالقاعدة دقيقة وآمنة.

الاستخدام برمجيًّا:
    from dagger_lexicon import apply_dagger
    corrected_classes = apply_dagger(letters, pred_classes)
"""
import sys
sys.path.insert(0, ".")
from data.vocab_v1d import split_letters_and_diacritics, merge_letters_and_diacritics

# كلمات حاملة الخنجريّة (مشكّلة بالكامل) — تُشتقّ الفئات آليًّا
CORE = [
    # أسماء الإشارة (مبنيّة، ثابتة)
    "هَٰذَا", "هَٰذِهِ", "هَٰذَانِ", "هَٰذَيْنِ", "هَٰؤُلَاءِ",
    "ذَٰلِكَ", "ذَٰلِكُمْ", "ذَٰلِكُمَا", "ذَٰلِكُنَّ", "كَذَٰلِكَ",
    "أُولَٰئِكَ", "هَٰكَذَا", "هَٰهُنَا",
    # لكنّ وأخواتها في الصورة
    "لَٰكِنْ", "لَٰكِنَّ", "لَٰكِنِ",
]
MAQSUR = [
    # مقصورات (الخنجريّة على الألف المقصورة) — الصورة المجرّدة فقط (المتّصلة بالضمير تختلف)
    "عَلَىٰ", "إِلَىٰ", "حَتَّىٰ", "مَتَىٰ", "لَدَىٰ", "أَنَّىٰ", "أَوْلَىٰ", "طُوبَىٰ",
]
NAMES = ["مُوسَىٰ", "عِيسَىٰ", "يَحْيَىٰ", "طَٰهَ"]
DIVINE = ["اللَّٰه", "الرَّحْمَٰن", "إِلَٰه", "إِلَٰهَ"]  # تحقّق بشريّ مستحبّ

# اللواصق البادئة المسموح بها (تبقى حركتها من النموذج)
PREFIXES = ["و", "ف", "ب", "ك", "ل", "وب", "ول", "وك", "فب", "فل", "فك", "بال", "ولل"]

def _build(words):
    lex = {}
    for w in words:
        L, C = split_letters_and_diacritics(w)
        lex["".join(L)] = tuple(C)
    return lex

LEX = {}
LEX.update(_build(CORE))
LEX.update(_build(MAQSUR))
LEX.update(_build(NAMES))
LEX.update(_build(DIVINE))

def _lookup(skel):
    if skel in LEX:
        return 0, LEX[skel]
    for p in PREFIXES:
        if skel.startswith(p) and skel[len(p):] in LEX:
            return len(p), LEX[skel[len(p):]]
    return None

def apply_dagger(letters, classes):
    """يُصحّح فئات الكلمات المطابقة للمعجم (يُبقي بقيّة تنبّؤات النموذج)."""
    classes = list(classes)
    words = []; s = None
    for i, ch in enumerate(letters):
        if ch == " ":
            if s is not None: words.append((s, i)); s = None
        else:
            if s is None: s = i
    if s is not None: words.append((s, len(letters)))
    hits = 0
    for a, b in words:
        skel = "".join(letters[a:b])
        r = _lookup(skel)
        if r is None: continue
        off, cls = r
        if a + off + len(cls) == b:
            for k, c in enumerate(cls):
                classes[a + off + k] = c
            hits += 1
    return classes, hits

if __name__ == "__main__":
    print(f"مدخلات المعجم: {len(LEX)}")
    # تحقّق round-trip
    bad = 0
    for w in CORE + MAQSUR + NAMES + DIVINE:
        L, C = split_letters_and_diacritics(w)
        if merge_letters_and_diacritics(L, C) != w:
            # قد يكون فرق ترتيب علامات فقط
            import unicodedata as U
            if U.normalize("NFC", merge_letters_and_diacritics(L, C)) != U.normalize("NFC", w):
                print(f"  ❌ {w} → {merge_letters_and_diacritics(L,C)}"); bad += 1
    print(f"round-trip: {'كلّها سليمة' if bad==0 else f'{bad} مشكلة'}")
    # اختبار اللواصق
    for t in ["وهذا", "فذلك", "بهذا", "لهذا", "وكذلك", "على", "عليه", "موسى"]:
        L, _ = split_letters_and_diacritics(t)
        cls = [0]*len(L)
        out, h = apply_dagger(L, cls)
        print(f"  {t}: {'طُبّق' if h else 'لا'} → {merge_letters_and_diacritics(L, out)}")
