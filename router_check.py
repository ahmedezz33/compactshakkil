# -*- coding: utf-8 -*-
"""فحص فهرس الاسترداد مباشرة (بلا نموذج) — لكشف حالة ملفّ القرآن على القرص."""
import sys
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DIAC = set("ًٌٍَُِّْٰ")
HAMZA = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
def _norm(s):
    return " ".join("".join(c for c in s if c not in DIAC).translate(HAMZA).split())

BISM = "بسم الله الرحمن الرحيم"
p = "data/raw/quran/quran-simple.txt"
lines = Path(p).read_text(encoding="utf-8").splitlines()
index = {}
def add(k, o):
    if k and k not in index:
        index[k] = o
for line in lines:
    o = line.strip()
    if not o:
        continue
    k = _norm(o); add(k, o)
    if k.startswith(BISM + " "):
        add(k[len(BISM) + 1:], " ".join(o.split()[4:]))

out = [f"أسطر الملفّ: {len(lines)}", f"حجم الفهرس: {len(index)}", ""]
# أطول سطر (لكشف هل كل سورة في سطر واحد)
longest = max(lines, key=lambda x: len(x.split()))
out.append(f"أطول سطر ({len(longest.split())} كلمة): {longest[:80]}...")
out.append("")
for t in ["انا اعطيناك الكوثر", "قل هو الله احد"]:
    inx = t in index
    out.append(f"'{t}'  in index = {inx}  → {index.get(t, 'MISSING')}")
    # ابحث عن السطر الذي يحويه
    hits = [l for l in lines if t in _norm(l)][:1]
    if hits:
        out.append(f"      السطر الحاوي: {hits[0][:90]}")

txt = "\n".join(out)
print(txt)
Path("router_check.txt").write_text(txt, encoding="utf-8")
