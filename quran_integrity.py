# -*- coding: utf-8 -*-
"""quran_integrity.py — حارسُ سلامةِ القرآن (حمايةً لرسمِ المصحفِ من التعديل).
يتحقّقُ أنّ ملفاتِ نصِّ القرآنِ ووحدةَ الاسترجاعِ لم تُغيَّرْ.
  استخدام:  from quran_integrity import verify; verify()      (تحذيريّ افتراضيًّا)
  صارم:     COMPACTSHAKKIL_STRICT_INTEGRITY=1  → يرفضُ العملَ عند التغيير.
  بعد تغييرٍ مقصودٍ موثَّق:  python quran_integrity.py generate
"""
import os, sys, json, hashlib
BASE = os.path.dirname(os.path.abspath(__file__))
PROTECTED = [
    "data/raw/quran/quran-simple.txt",        # رسمُ المصحفِ (مع الخنجريّة) — نصُّ Tanzil، تعديلُه ممنوع
    "data/raw/quran/quran-simple-plain.txt",  # الرسمُ العاديّ
    "reverence_aware_unified.py",             # منطقُ الاسترجاعِ القرآنيّ
]
MANIFEST = os.path.join(BASE, "quran_integrity.json")
def _sha(rel):
    h = hashlib.sha256()
    with open(os.path.join(BASE, rel), "rb") as f:
        for ch in iter(lambda: f.read(65536), b""): h.update(ch)
    return h.hexdigest()
def current():
    return {p: _sha(p) for p in PROTECTED if os.path.exists(os.path.join(BASE, p))}
def generate():
    data = {"_note": "بصماتُ سلامةِ القرآن — لا تُعدَّلْ يدويًّا. أعِدِ التوليدَ فقط بعدَ تغييرٍ مقصودٍ موثَّق.",
            "hashes": current()}
    json.dump(data, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("تولّدت البصمات:", MANIFEST)
    for k, v in data["hashes"].items(): print("  ", k, "=", v[:16], "...")
def verify(strict=None):
    if strict is None:
        strict = os.environ.get("COMPACTSHAKKIL_STRICT_INTEGRITY", "0") == "1"
    if not os.path.exists(MANIFEST):
        print("[سلامة القرآن] لا يوجدُ ملفُّ بصمات — تخطّي الفحص."); return True
    exp = json.load(open(MANIFEST, encoding="utf-8")).get("hashes", {})
    cur = current()
    bad = [p for p in exp if cur.get(p) != exp[p]]
    if not bad:
        return True
    msg = ("[سلامة القرآن] اكتُشِفَ تغييرٌ في ملفاتٍ محميّة: " + "، ".join(bad) +
           "\n  رسمُ المصحفِ واسترجاعُه لا يجوزُ تعديلُهما (راجعْ NOTICE وترخيصَ Tanzil).")
    if strict: raise SystemExit(msg)
    print(msg); print("  (تحذيريّ — للصرامة: COMPACTSHAKKIL_STRICT_INTEGRITY=1)")
    return False
if __name__ == "__main__":
    (generate if len(sys.argv) > 1 and sys.argv[1] == "generate" else verify)()
