# -*- coding: utf-8 -*-
"""
merge_corpus.py — يبني مدوّنةَ تدريبٍ موسَّعةً للتشكيل: Tashkeela + نصوص الشاملة المستخرَجة.

يقرأُ الكتبَ المستخرَجةَ (data/shamela_corpus/*.txt)، يُقطّعُها جُملًا، يُبقي
المشكَّلَ جيّدًا فقط، يحذفُ المكرَّرَ، **ويمنعُ تسرُّبَ الاختبار** (يحذفُ أيَّ جملةٍ
تطابقُ سطرًا في مجموعة الاختبار). ثمّ يدمجُها مع data/processed_max/train.txt.

    python merge_corpus.py            # يبني data/processed_ft/train.txt
"""
import os, re, sys, glob

BASE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(BASE, "data", "shamela_corpus")
BASE_TRAIN = os.path.join(BASE, "data", "processed_max", "train.txt")
TEST_NOLEAK = os.path.join(BASE, "data", "processed_clean", "test_noleak.txt")
OUT_DIR = os.path.join(BASE, "data", "processed_ft")
OUT_TRAIN = os.path.join(OUT_DIR, "train.txt")

_HARAKAT = "ًٌٍَُِّْٰ"
_AR = re.compile(r"[ء-ي]")
_SPLIT = re.compile(r"[.!?؟\n۔]|(?<=[ء-ي])،(?=\s)")   # حدودُ الجُمل


def _strip_marks(s):
    return "".join(c for c in s if c not in _HARAKAT)


def harakat_ratio(s):
    letters = _AR.findall(s)
    if not letters:
        return 0.0
    marks = sum(1 for c in s if c in _HARAKAT)
    return marks / max(1, len(letters))


def clean_line(s):
    s = re.sub(r"[^؀-ۿ\s]", " ", s)      # عربيٌّ + حركاتٌ فقط
    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    return s


def sentences_from(text):
    for chunk in _SPLIT.split(text):
        if not chunk:
            continue
        s = clean_line(chunk)
        w = s.split()
        if len(w) < 3 or len(w) > 40:              # جُملٌ معقولةُ الطول
            continue
        if harakat_ratio(s) < 0.5:                 # مشكَّلةٌ جيّدًا فقط
            continue
        yield s


def load_test_keys():
    keys = set()
    if os.path.exists(TEST_NOLEAK):
        for line in open(TEST_NOLEAK, encoding="utf-8"):
            b = _strip_marks(line.strip())
            if b:
                keys.add(b)
    return keys


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    test_keys = load_test_keys()
    print(f"مفاتيحُ الاختبار (للحماية من التسرُّب): {len(test_keys):,}")

    seen = set()
    new_sents = []
    files = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt")))
    print(f"كتبُ الشاملة المستخرَجة: {len(files)}")
    for fp in files:
        txt = open(fp, encoding="utf-8", errors="ignore").read()
        for s in sentences_from(txt):
            b = _strip_marks(s)
            if b in test_keys:                     # تسرُّبٌ ← احذف
                continue
            if b in seen:                          # مكرَّر
                continue
            seen.add(b)
            new_sents.append(s)
    print(f"جُملٌ جديدةٌ من الشاملة (بعد التنظيف/إزالة التسرُّب والتكرار): {len(new_sents):,}")

    n_base = 0
    with open(OUT_TRAIN, "w", encoding="utf-8") as out:
        if os.path.exists(BASE_TRAIN):
            for line in open(BASE_TRAIN, encoding="utf-8"):
                if line.strip():
                    out.write(line if line.endswith("\n") else line + "\n")
                    n_base += 1
        for s in new_sents:
            out.write(s + "\n")
    print(f"✅ كُتِب {OUT_TRAIN}")
    print(f"   الأساس (Tashkeela): {n_base:,} سطر + الشاملة: {len(new_sents):,} = "
          f"{n_base + len(new_sents):,} إجمالًا")
    if not new_sents:
        print("⚠️ لا نصوصَ شاملة بعد. استخرجْ كتبًا أولًا: run_extract_book.bat --all-volumes")


if __name__ == "__main__":
    main()
