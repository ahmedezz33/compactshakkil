# -*- coding: utf-8 -*-
import sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
print("… تحميل محلّل CAMeL الصرفيّ (calima-msa)")
try:
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.morphology.analyzer import Analyzer
except Exception as e:
    print("فشل الاستيراد:", e); raise SystemExit
try:
    db = MorphologyDB.builtin_db()
    an = Analyzer(db)
except Exception as e:
    print("فشل تحميل القاعدة (جرّب: venv\\Scripts\\camel_data -i light):", e); raise SystemExit

WORDS = ["خيم","ضرب","حول","عزة","الثمن","فرحة"]
for w in WORDS:
    try:
        analyses = an.analyze(w)
    except Exception as e:
        print(w, "خطأ:", e); continue
    seen=[]; 
    for a in analyses:
        key=(a.get('diac',''), a.get('pos',''), a.get('cas',''))
        if key not in seen: seen.append(key)
    print("="*60)
    print(f"«{w}» — عدد القراءات الفريدة: {len(seen)}")
    for diac,pos,cas in seen[:14]:
        print(f"   {diac:<16} pos={pos:<10} cas={cas}")
print("="*60)
