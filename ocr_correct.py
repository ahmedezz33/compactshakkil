# -*- coding: utf-8 -*-
"""
ocr_correct.py — مصحّحٌ لُغويٌّ لأخطاء الـ OCR بالاعتماد على معجم arabic_lexicon.db.
لكلِّ كلمةٍ: إن كان رسمُها المجرّدُ في المعجم تُترَك (بحركاتها من OCR)؛ وإلّا يُبحَثُ
عن أقرب كلمةٍ صحيحة (مسافةُ تحرير ١) وتُستبدَلُ بصورتها المشكَّلة من المعجم.
"""
import os, re, sqlite3, unicodedata
BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,"lexicon","arabic_lexicon.db")
_LOADED=False; _BARE=set(); _FREQ={}; _DIAC={}
_AR="ابتثجحخدذرزسشصضطظعغفقكلمنهوياءأإآئؤىة"
_MARKS=re.compile(r"[ً-ْٰ]")
_DIAC_RE=re.compile(r'"diac"\s*:\s*"([^"]+)"')

def _bare(w): return _MARKS.sub("", w).replace("ٱ","ا")

def load():
    global _LOADED
    if _LOADED: return
    try:
        con=sqlite3.connect(f"file:{DB}?mode=ro",uri=True); cur=con.cursor()
        for word,freq,aj in cur.execute("SELECT word,frequency,analyses_json FROM words"):
            b=_bare(word or "")
            if not b: continue
            _BARE.add(b)
            if freq and (b not in _FREQ or freq>_FREQ[b]):
                _FREQ[b]=freq or 0
                m=_DIAC_RE.search(aj or "")
                if m: _DIAC[b]=m.group(1)
        con.close()
    except Exception as e:
        print("lexicon load err:",e)
    _LOADED=True

def _edits1(w):
    sp=[(w[:i],w[i:]) for i in range(len(w)+1)]
    dele=[a+b[1:] for a,b in sp if b]
    trans=[a+b[1]+b[0]+b[2:] for a,b in sp if len(b)>1]
    repl=[a+c+b[1:] for a,b in sp if b for c in _AR]
    ins=[a+c+b for a,b in sp for c in _AR]
    return set(dele+trans+repl+ins)

def _fix_word(core):
    b=_bare(core)
    if len(b)<3 or b in _BARE: return core, False        # صحيحةٌ أو قصيرة
    cands=[w for w in _edits1(b) if w in _BARE]
    if not cands: return core, False
    best=max(cands, key=lambda w:_FREQ.get(w,0))
    if _FREQ.get(best,0) < 200: return core, False        # تجنّبِ التصحيحَ لكلمةٍ نادرة
    return _DIAC.get(best, best), True

def correct(text):
    """يرجع (النصّ المصحَّح، عددُ التصحيحات)."""
    if not text: return text, 0
    load()
    n=0; out_lines=[]
    for line in text.split("\n"):
        toks=[]
        for tok in line.split(" "):
            m=re.match(r"^([^\wء-ي]*)(.*?)([^\wء-ي]*)$", tok, re.S)
            pre,core,post=(m.group(1),m.group(2),m.group(3)) if m else ("",tok,"")
            if core:
                fixed,ch=_fix_word(core)
                if ch: n+=1
                toks.append(pre+fixed+post)
            else:
                toks.append(tok)
        out_lines.append(" ".join(toks))
    return "\n".join(out_lines), n
