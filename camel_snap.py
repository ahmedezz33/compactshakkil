# -*- coding: utf-8 -*-
"""camel_snap.py — تقييدُ مخرجِ المشكِّلِ بقراءاتِ محلِّل CAMeL الصرفيّ الصحيحة.
يستبدلُ أيَّ صورةٍ غيرِ جائزةٍ صرفيًّا بأقربِ قراءةٍ صحيحةٍ (مسافةُ تحريرٍ على التشكيل)،
فلا يخرجُ النظامُ بصورةٍ مستحيلة. الأعلامُ والكلماتُ غيرُ المعروفةِ تبقى كما أخرجها المشكِّل.
طبقةُ تصحيحٍ بعد النموذج، لا بديلٌ عنه. تُقاسُ على المعيارِ قبل التفعيل."""
import functools

_HARAKAT = set("ًٌٍَُِّْ") | {"ـ"}   # تنوين/حركات/شدة/سكون/تطويل
def _strip(s): return "".join(c for c in s if c not in _HARAKAT)

_AN = None
def _analyzer():
    global _AN
    if _AN is None:
        from camel_tools.morphology.database import MorphologyDB
        from camel_tools.morphology.analyzer import Analyzer
        _AN = Analyzer(MorphologyDB.builtin_db())
    return _AN

def _lev(a, b):
    m, n = len(a), len(b)
    if not m: return n
    if not n: return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        ai = a[i - 1]
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ai != b[j - 1]))
        prev = cur
    return prev[n]

@functools.lru_cache(maxsize=100000)
def _cands(bare):
    try:
        return tuple(sorted({a['diac'] for a in _analyzer().analyze(bare) if a.get('diac')}))
    except Exception:
        return tuple()

# تطبيعُ الاصطلاحِ للمقارنةِ فقط: نُسقِطُ الشدّةَ والسكونَ ونوحّدُ الألفَ/التاء/الياء،
# فلا نَعُدَّ فرقَ الاصطلاحِ (شدّةُ اللامِ الشمسيّة، السكون) خطأً. نُبقي الحركاتِ القصيرةَ والتنوين.
_NORMT = str.maketrans({"\u0651":"", "\u0652":"", "أ":"ا","إ":"ا","آ":"ا","ٱ":"ا", "ى":"ي", "ة":"ه"})
def _norm(s): return s.translate(_NORMT)

@functools.lru_cache(maxsize=200000)
def snap_word(diac):
    """يُبقي مخرجَ BERT إن كان جائزًا تحت الاصطلاح (ولو أغنى تشكيلًا)؛
    ولا يستبدلُه إلّا إن كانت صورتُه مستحيلةً صرفيًّا؛ والأعلامُ تبقى كما هي."""
    bare = _strip(diac)
    if len(bare) < 2: return diac
    cands = _cands(bare)
    if not cands: return diac               # عَلَمٌ/غيرُ معروفٍ ← اترك المشكِّل
    nb = _norm(diac)
    for c in cands:
        if _norm(c) == nb:                  # جائزٌ تحت الاصطلاح ← أبقِ BERT الأغنى
            return diac
    # صورةٌ مستحيلةٌ حقًّا (نادرة) ← أقربُ قراءةٍ صحيحة
    return min(cands, key=lambda c: (_lev(_norm(c), nb), abs(len(c) - len(diac))))

def snap_text(text):
    out = []
    for line in text.split("\n"):
        out.append(" ".join(snap_word(w) if w.strip() else w for w in line.split(" ")))
    return "\n".join(out)

# ───────── الدمجُ (ملءُ الفراغِ فقط، لا استبدال) — فكرةُ أحمد ─────────
from data.vocab_v2 import split_letters_and_diacritics as _SPL, merge_letters_and_diacritics as _MRG
_FILLED=[0]
def fill_word(diac):
    """ملءٌ صارم: يُبقي كلَّ حركاتِ BERT، ويملأُ حرفًا فارغًا فقط إن (١) ليس آخِرَ الكلمة،
    و(٢) أجمعتْ كلُّ قراءاتِ CAMeL المتوافقةِ مع حركاتِ BERT على نفسِ الحركةِ لذلك الحرف."""
    L,D=_SPL(diac)
    if 0 not in D: return diac
    cands=_cands(_strip(diac))
    if not cands: return diac
    comp=[]
    for c in cands:
        cL,cD=_SPL(c)
        if cL==L and all(D[i]==0 or D[i]==cD[i] for i in range(len(D))):
            comp.append(cD)
    if not comp: return diac
    merged=list(D); last=len(D)-1
    for i in range(len(D)):
        if i==last or D[i]!=0: continue
        marks={cd[i] for cd in comp}
        if len(marks)==1:
            m=next(iter(marks))
            if m!=0: merged[i]=m
    _FILLED[0]+=sum(1 for i in range(len(D)) if D[i]==0 and merged[i]!=0)
    return _MRG(L,merged) if merged!=D else diac

def fill_text(text):
    return "\n".join(" ".join(fill_word(w) if w.strip() else w for w in ln.split(" ")) for ln in text.split("\n"))
