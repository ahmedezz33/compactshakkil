# -*- coding: utf-8 -*-
"""gazetteer.py — قاموسُ أعلامٍ يدويّ. يُصحّحُ تشكيلَ الأعلامِ المُدرجةِ فقط،
ويُبقي حركةَ الآخِرِ من النموذج (الإعراب يُحدّدُه السياق). آمنٌ: لا يمسُّ غيرَ المُدرَج."""
import os, json
from data.vocab_v2 import split_letters_and_diacritics as _SPL, merge_letters_and_diacritics as _MRG, strip_diacritics as _STR
_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)),"name_overrides.json")
_G=None; _MT=None
def _load():
    global _G,_MT
    try: mt=os.path.getmtime(_PATH)
    except OSError: return {}
    if _G is not None and mt==_MT: return _G
    try:
        raw=json.load(open(_PATH,encoding="utf-8"))
        _G={_STR(k):v for k,v in raw.items() if not str(k).startswith("_") and isinstance(v,str)}
    except Exception: _G={}
    _MT=mt; return _G
def apply_word(word):
    g=_load(); bare=_STR(word)
    if bare not in g: return word
    canon=g[bare]
    cL,cD=_SPL(canon); wL,wD=_SPL(word)
    if cL!=wL or not wD: return canon
    merged=list(cD); merged[-1]=wD[-1]   # داخليّ من القاموس، آخِرُ الحركةِ من النموذج
    return _MRG(wL,merged)
def apply_text(text):
    return "\n".join(" ".join(apply_word(w) if w.strip() else w for w in ln.split(" ")) for ln in text.split("\n"))
