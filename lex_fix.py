# -*- coding: utf-8 -*-
"""lex_fix.py — طبقةُ تصحيحٍ معجميّةٌ آمنةٌ (ثوابتُ بلا خلاف + أعلام) بعدَ النموذج.
- fixed_forms.json: كلماتٌ مبنيّةٌ تشكيلُها كاملٌ لا يتغيّرُ بالسياق ← تُفرَضُ كاملةً.
- name_overrides.json (عبر gazetteer): أعلامٌ ← داخليٌّ من القاموس، آخِرُ الحركةِ من النموذج.
تُطبَّقُ على مخرجِ BERT-graft فقط (لا تمسُّ القرآنَ المسترَدّ). قيسَتْ: صفرُ تراجعٍ على المعيار."""
import os, json
from data.vocab_v2 import strip_diacritics as _STR
import gazetteer

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixed_forms.json")
_F = None; _MT = None
def _load():
    global _F, _MT
    try: mt = os.path.getmtime(_PATH)
    except OSError: return {}
    if _F is not None and mt == _MT: return _F
    try:
        raw = json.load(open(_PATH, encoding="utf-8"))
        _F = {_STR(k): v for k, v in raw.items() if not str(k).startswith("_") and isinstance(v, str)}
    except Exception: _F = {}
    _MT = mt; return _F

def apply_word(word):
    if not word.strip(): return word
    f = _load(); b = _STR(word)
    if b in f: return f[b]              # ثابتٌ مبنيٌّ: الشكلُ كاملًا
    return gazetteer.apply_word(word)   # عَلَمٌ (آخِرٌ من النموذج) أو يُرجِعُه كما هو

def apply_text(text):
    return "\n".join(" ".join(apply_word(w) for w in ln.split(" ")) for ln in text.split("\n"))
