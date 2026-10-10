# -*- coding: utf-8 -*-
"""
quran_audio.py — تلاوةٌ حقيقيّةٌ محلّيّةٌ للقرآن (آية-آية) بصوت قارئ.

الفكرة: نرقّم كلَّ آيةٍ (سورة:آية) من فهرس القرآن المرتَّب (٦٢٣٦ آية، حفص)، ثمّ
نطابق أيَّ نصٍّ مُدخَلٍ بآيته ونشغّل ملفَّ تلاوتها المحلّيّ recordings/quran/SSSAAA.mp3
(يُنزَّل مرّةً بـ download_quran_audio.py). نطقٌ صحيحٌ ١٠٠٪ بكلّ التجويد.
مستقلٌّ عن torch (تطبيعٌ خفيفٌ عبر vocab_v2.strip_diacritics).
"""
import os, re, difflib
_THR1=float(os.environ.get('QURAN_THR1','0.82'))
_THR2=float(os.environ.get('QURAN_THR2','0.78'))
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from data.vocab_v2 import strip_diacritics as _SD

_BASE=os.path.dirname(os.path.abspath(__file__))
QURAN = os.path.join(_BASE,"data","raw","quran","quran-simple.txt")
QDIR  = os.path.join(_BASE,"recordings","quran")
WDIR  = os.path.join(_BASE,"train_data","minshawy","wavs")  # مدوّنةُ التلاوة الحقيقيّة (٦٢٣٦ آية)

# عددُ آيات كلّ سورةٍ (حفص) — المجموع ٦٢٣٦
SURA_AYAT = [7,286,200,176,120,165,206,75,129,109,123,111,43,52,99,128,111,110,98,
135,112,78,118,64,77,227,93,88,69,60,34,30,73,54,45,83,182,88,75,85,54,53,89,59,
37,35,38,29,18,45,60,49,62,55,78,96,29,22,24,13,14,11,11,18,12,12,30,52,52,44,28,
28,20,56,40,31,50,40,46,42,29,19,36,25,22,17,19,26,30,20,15,21,11,8,8,19,5,8,8,11,
11,8,3,9,5,4,7,3,6,3,5,4,5,6]

# ── تطبيعٌ موحّدٌ (مطابقٌ لطبقة الاسترداد) ─────────────────────────────
_SMALL_ALIF="ٰ"; _TATWEEL="ـ"
_NORM_MAP=str.maketrans({"أ":"ا","إ":"ا","آ":"ا","ٱ":"ا","ؤ":"و","ئ":"ي","ء":"",
                         "ى":"ي","ة":"ه",_SMALL_ALIF:"ا"})
_QMARKS=re.compile(r"[ؐ-ًؚ-ٟۖ-ۭ࣓-ࣿ]")
_KEEP=re.compile(r"[^ء-ي ]")
def _norm(s):
    s=_SD(s).replace(_TATWEEL,""); s=_QMARKS.sub("",s); s=s.translate(_NORM_MAP)
    for _a,_b in (("صلواه","صلاه"),("زكواه","زكاه"),("حيواه","حياه"),("ربواا","ربا")):
        s=s.replace(_a,_b)
    return " ".join(_KEEP.sub(" ",s).split())

_BISM=_norm("بسم الله الرحمن الرحيم")

def _lines(path):
    out=[]
    try: raw=Path(path).read_text(encoding="utf-8").splitlines()
    except Exception: return out
    for l in raw:
        s=" ".join(l.strip().lstrip("﻿").split())
        if s and not s.startswith("#"): out.append(s)
    return out

_PLAIN=os.path.join(_BASE,"data","raw","quran","quran-simple-plain.txt")
_MAP=None
_SEQ=None
def _build():
    """خريطةُ: مفتاحُ التطبيع → رمزُ الآية SSSAAA — من النسختين (خنجريّة/مجرّد) لتغطية
    كلِّ صور الرسم والكتابة، ومن نسخةٍ تسدّ نقصَ الأخرى."""
    global _MAP
    if _MAP is not None: return _MAP
    _MAP={}
    editions=[e for e in (_lines(QURAN), _lines(_PLAIN)) if len(e)==6236]
    if not editions: editions=[_lines(QURAN)]
    for lines in editions:
        i=0
        for s,cnt in enumerate(SURA_AYAT, start=1):
            for a in range(1, cnt+1):
                if i>=len(lines): break
                code=f"{s:03d}{a:03d}"; k=_norm(lines[i]); i+=1
                if k: _MAP.setdefault(k, code)
                if k.startswith(_BISM+" "):          # آيةٌ أوّلُها بسملة → أضِف المجرّدة
                    kr=" ".join(k.split()[4:])
                    if kr: _MAP.setdefault(kr, code)
    global _SEQ
    if _SEQ is None:
        base=editions[0] if editions else []
        BISM="".join(_norm(base[0]).split()) if base else ""   # 1:1 = البسملة نفسها
        _SEQ=[]; i=0
        for si,cnt in enumerate(SURA_AYAT, start=1):
            for a in range(1, cnt+1):
                if i>=len(base): break
                code=f"{si:03d}{a:03d}"
                ns="".join(_norm(base[i]).split())
                if a==1 and si!=1 and BISM and ns.startswith(BISM) and len(ns)>len(BISM):
                    ns=ns[len(BISM):]                          # انزع البسملةَ المُقحَمة
                _SEQ.append((code, ns)); i+=1
    return _MAP

def ayah_code(text, fuzzy=True):
    """رمزُ الآية (SSSAAA) إن طابق النصُّ آيةً تامّة، وإلّا None.
    fuzzy: عند فشل التطابق التامّ، يبحثُ عن أقرب آيةٍ (يتحمّلُ أخطاءَ OCR البسيطة)."""
    if not text or not text.strip(): return None
    m=_build(); k=_norm(text)
    c=m.get(k)
    if c or not fuzzy: return c
    if len(k.split())<3: return None            # نصوصٌ قصيرةٌ: لا مطابقةَ تقريبيّة
    cand=difflib.get_close_matches(k, m.keys(), n=1, cutoff=0.9)
    return m[cand[0]] if cand else None

def _wav_for(code):
    for base,ext in ((WDIR,".wav"),(QDIR,".mp3"),(QDIR,".wav"),(WDIR,".mp3")):
        p=os.path.join(base, code+ext)
        if os.path.exists(p): return p
    return None

_START=None
def _seg_index():
    """فهرسُ التقسيم: أوّلُ كلمةٍ ← [(رمز، كلماتُ الآية)] مرتَّبةً بالأطول أوّلًا."""
    global _START
    if _START is not None: return _START
    m=_build(); _START={}
    for txt,code in m.items():
        w=txt.split()
        if w: _START.setdefault(w[0],[]).append((code,tuple(w)))
    for k in _START: _START[k].sort(key=lambda x:-len(x[1]))
    return _START

def _ratio(a,b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def segment_codes(text, thr=0.8, cover=0.8):
    """قسّمِ النصَّ إلى تسلسلِ آياتٍ متتابعة، بتسامحٍ مع اختلاف الرسم وفصلِ الكلمات.
    ١) تطابقٌ تامٌّ سريعٌ على الكلمات. ٢) وإلّا مطابقةٌ على مستوى الحروف (بلا مسافات):
    تحديدُ آيةِ البداية بأقربِ تطابقٍ ثمّ السيرُ بالترتيب المصحفيّ."""
    if not text or not text.strip(): return None
    _build()
    # (١) المسارُ السريع: تطابقٌ تامّ على الكلمات
    words=_norm(text).split()
    if len(words)>=2:
        idx=_seg_index(); i=0; codes=[]; ok=True
        while i<len(words):
            hit=None
            for code,wt in idx.get(words[i],()):
                L=len(wt)
                if L and tuple(words[i:i+L])==wt: hit=(code,L); break
            if not hit: ok=False; break
            codes.append(hit[0]); i+=hit[1]
        if ok and codes: return codes
    # (٢) المسارُ المتسامح على مستوى الحروف
    P="".join(words)
    seq=_SEQ or []
    if len(P)<6 or not seq: return None
    best=None
    for si,(code,ns) in enumerate(seq):
        L=min(len(ns),len(P))
        if L<3: continue
        sc=_ratio(P[:L], ns[:L])
        if best is None or sc>best[0]: best=(sc,si)
    if not best or best[0]<thr: return None
    si=best[1]; pos=0; codes=[]
    while pos<len(P) and si<len(seq):
        code,ns=seq[si]; L=len(ns); seg=P[pos:pos+L]
        if not seg: break
        sc=_ratio(seg, ns)
        if sc>=thr or (len(seg)<L and sc>=0.55):
            codes.append(code); pos+=L; si+=1
        else:
            break
    if codes and pos>=len(P)*cover:
        return codes
    return None

def _concat_codes(codes, gap_ms=150):
    """ادمجْ تلاواتِ الآيات في ملفٍّ واحدٍ (بفاصلٍ طبيعيٍّ بينها)."""
    try:
        import numpy as np, soundfile as sf, tempfile
    except Exception:
        return None
    parts=[]; sr0=None
    for c in codes:
        p=_wav_for(c)
        if not p: return None
        x,sr=sf.read(p,dtype="float32")
        if getattr(x,"ndim",1)>1: x=x.mean(1)
        if sr0 is None: sr0=sr
        if sr!=sr0:
            n=int(len(x)*sr0/sr)
            x=np.interp(np.linspace(0,len(x),n,endpoint=False),np.arange(len(x)),x).astype("float32")
        parts.append(x); parts.append(np.zeros(int(sr0*gap_ms/1000),dtype="float32"))
    if not parts: return None
    out=np.concatenate(parts)
    tag="_".join(codes[:2])+("" if len(codes)<=2 else f"_{len(codes)}ayat")
    tp=os.path.join(tempfile.gettempdir(), "quran_"+tag+".wav")
    sf.write(tp,out,sr0,subtype="PCM_16")
    return tp

_C2NS=None; _C2IDX=None
def _maps():
    global _C2NS,_C2IDX
    if _C2NS is None:
        _build(); seq=_SEQ or []
        _C2NS={c:ns for c,ns in seq}
        _C2IDX={c:i for i,(c,ns) in enumerate(seq)}
    return _C2NS,_C2IDX

def _match_here(wn, i, target, thr=0.83):
    """كم كلمةً (من wn ابتداءً من i) تطابقُ آيةً نصُّها target (بلا مسافات)؟ 0 إن لا."""
    if not target: return 0
    best=(0.0,0); cur=""; n=len(wn)
    kmax=min(n-i, 60)
    for k in range(1, kmax+1):
        cur+=wn[i+k-1]
        if len(cur) < len(target)*0.6: continue
        r=_ratio(cur, target)
        if r>best[0]: best=(r,k)
        if len(cur) > len(target)*1.5: break
    return best[1] if best[0]>=thr else 0

MIN_QURAN_WORDS=5

# ── نصُّ الآيةِ المشكَّلُ الكامل (من metadata.csv) لاستردادِ تشكيلِ المصحف ──
_DIAC=None
def _diac_map():
    global _DIAC
    if _DIAC is None:
        _DIAC={}
        mp=os.path.join(_BASE,"train_data","minshawy","metadata.csv")
        try:
            with open(mp,encoding="utf-8") as fh:
                next(fh,None)
                for line in fh:
                    if "|" not in line: continue
                    a,t=line.rstrip("\n").split("|",1)
                    mm=re.search(r"(\d{6})", a)          # الرمزُ من المسار (يعملُ مع / و \\)
                    if mm: _DIAC[mm.group(1)]=t.strip()
        except Exception as e:
            print("diac map:",e)
    return _DIAC

def ayah_diac(code):
    """النصُّ القرآنيُّ المشكَّلُ الصحيحُ للرمز (من المصحف)، أو None."""
    return _diac_map().get(code)

_BRACE=re.compile(r"[\u276f\uFD3F{]([^\u276e\uFD3E}]*)[\u276e\uFD3E}]")
# ملاحظة: ﴿=U+FD3F ﴾=U+FD3E ؛ نقبلُ أيضًا { } العاديّتين

def codes_diac(codes):
    """يجمعُ النصَّ المشكَّلَ لعدّةِ آياتٍ بمسافةٍ بينها."""
    return " ".join(ayah_diac(c) or "" for c in codes).strip()

def restore_quran_tashkeel(text):
    """يستبدلُ محتوى الأقواسِ ﴿﴾/{} بالنصِّ القرآنيِّ المشكَّلِ الصحيحِ من المصحف (للعرض)."""
    if not text or not _BRACE.search(text): return text
    def _rep(m):
        inner=m.group(1)
        codes=segment_codes(inner)
        if codes:
            dt=codes_diac(codes)
            if dt: return "\uFD3F"+dt+"\uFD3E"       # ﴿ ... ﴾
        return m.group(0)
    return _BRACE.sub(_rep, text)

def _split_plain(text, MIN_QURAN_WORDS=MIN_QURAN_WORDS):
    """يقسّمُ نصًّا مختلطًا إلى مقاطعَ بالترتيب:
    {'type':'quran','codes':[...]} لأجزاء القرآن، {'type':'text','text':'...'} للعاديّ."""
    if not text or not text.strip(): return [{"type":"text","text":text or ""}]
    _build()
    wo=text.split(); wn=[_norm(w) for w in wo]
    idx=_seg_index(); c2ns,c2idx=_maps(); seq=_SEQ or []
    segs=[]; buf=[]; i=0; n=len(wo)
    while i<n:
        matched=False
        for code,wt in idx.get(wn[i],()):
            target=c2ns.get(code,"")
            if len(target)<8: continue                 # تجاهل الآياتِ القصيرة جدًّا (تقليلُ الخطأ)
            k=_match_here(wn, i, target, thr=_THR1)
            if k>0:
                codes=[code]; j=i+k; ci=c2idx.get(code)
                while ci is not None and ci+1<len(seq) and j<n:   # مدِّدْ بالترتيب المصحفيّ
                    ncode,nns=seq[ci+1]
                    k2=_match_here(wn, j, nns, thr=_THR2)
                    if k2>0: codes.append(ncode); j+=k2; ci+=1
                    else: break
                if (j-i) >= MIN_QURAN_WORDS:            # لا يقلُّ جزءُ القرآن عن ٥ كلمات
                    if buf: segs.append({"type":"text","text":" ".join(buf)}); buf=[]
                    segs.append({"type":"quran","codes":codes}); i=j; matched=True; break
                else:
                    buf.extend(wo[i:j]); i=j; matched=True; break   # قصيرٌ ← يُعامَلُ نصًّا عاديًّا
        if not matched:
            buf.append(wo[i]); i+=1
    if buf: segs.append({"type":"text","text":" ".join(buf)})
    return segs

def split_quran_spans(text, MIN_QURAN_WORDS=MIN_QURAN_WORDS):
    """يقسّمُ نصًّا مختلطًا؛ يكشفُ الآياتِ المحصورةَ بأقواسٍ ﴿﴾/{} أوّلًا (دقيقٌ جدًّا)،
    ثمّ يُفوّضُ الباقيَ للكشفِ الكلميّ."""
    if not text or not text.strip(): return [{"type":"text","text":text or ""}]
    if not _BRACE.search(text):
        return _split_plain(text, MIN_QURAN_WORDS)
    out=[]; pos=0
    for m in _BRACE.finditer(text):
        pre=text[pos:m.start()]
        if pre.strip(): out.extend(_split_plain(pre, MIN_QURAN_WORDS))
        codes=segment_codes(m.group(1))
        if codes:
            out.append({"type":"quran","codes":codes})
        else:
            out.append({"type":"text","text":m.group(0)})
        pos=m.end()
    tail=text[pos:]
    if tail.strip(): out.extend(_split_plain(tail, MIN_QURAN_WORDS))
    return out or [{"type":"text","text":text}]

def restore_quran_strong(text, mark=False, min_words=None):
    """تقويةُ الاسترداد: يستردُّ تشكيلَ المصحفِ لكلِّ آيةٍ مكتشَفةٍ
    (مقوّسةً أو غيرَ مقوّسة) عبرَ الكاشفِ الكلميّ. يُبقي النصَّ العاديَّ كما هو.
    mark=True → يلفُّ الآيةَ بـ ﴿ ﴾. حذِرٌ: العتباتُ صارمةٌ لتقليلِ الالتباس."""
    if not text or not text.strip():
        return text
    try:
        kw = {} if min_words is None else {"MIN_QURAN_WORDS": min_words}
        spans = split_quran_spans(text, **kw)
    except Exception:
        return text
    if not any(sp.get("type") == "quran" for sp in spans):
        return text
    L, R = "﴿", "﴾"
    out = []
    for sp in spans:
        if sp.get("type") == "quran":
            d = codes_diac(sp.get("codes") or [])
            if d:
                out.append((L + d + R) if mark else d)
        else:
            t = sp.get("text", "")
            if t.strip():
                out.append(t)
    return " ".join(out).strip() or text


def audio_path(text):
    """مسارُ تلاوةِ الآية (واحدة) أو المقطع (عدّة آياتٍ متتابعة) محلّيًّا، وإلّا None."""
    c=ayah_code(text)
    if c:
        p=_wav_for(c)
        if p: return p
    codes=segment_codes(text)
    if codes and len(codes)>=2:
        return _concat_codes(codes)
    return None

def all_codes():
    """كلُّ رموز الآيات (للتنزيل)."""
    out=[]
    for s,cnt in enumerate(SURA_AYAT, start=1):
        for a in range(1, cnt+1): out.append(f"{s:03d}{a:03d}")
    return out

# ════════ استرداد القرآن الجزئيّ: يتعرّف على جزءٍ من الآية (ولو وسطها) ويستردّها كاملةً ════════
_AW=None; _INV=None
def _ayah_words():
    """قائمة (رمز، كلماتٌ مطبَّعة) لكلّ آية، بترتيب المصحف (مع نزع البسملة المُقحَمة)."""
    global _AW
    if _AW is not None: return _AW
    lines=_lines(QURAN); BISM=_norm(lines[0]).split() if lines else []
    aw=[]; i=0
    for si,cnt in enumerate(SURA_AYAT,start=1):
        for a in range(1,cnt+1):
            if i>=len(lines): break
            w=_norm(lines[i]).split(); i+=1
            if a==1 and si!=1 and BISM and w[:len(BISM)]==BISM and len(w)>len(BISM):
                w=w[len(BISM):]
            if w: aw.append((f"{si:03d}{a:03d}", w))
    _AW=aw; return aw

def _word_index():
    """فهرس: كلمة ← [(فهرسُ الآية، موضعُها فيها)] لتثبيتٍ من أيِّ موضع."""
    global _INV
    if _INV is not None: return _INV
    inv={}
    for ai,(code,w) in enumerate(_ayah_words()):
        for p,wd in enumerate(w): inv.setdefault(wd,[]).append((ai,p))
    _INV=inv; return inv

def _weq(a,b):
    if a==b: return True
    if len(a)<3 or len(b)<3: return False
    return difflib.SequenceMatcher(None,a,b).ratio()>=0.8

def restore_quran_partial(text, min_run=5, mark=False):
    """يتعرّف على جزءٍ من الآية (ولو كان وسطَها) ويستبدله بالآيةِ كاملةً من المصحف.
    يستبقي النصّ غير القرآنيّ كما هو. min_run: أقلّ عددِ كلماتٍ متتاليةٍ مطابقةٍ للتثبيت (ضدّ الخطأ)."""
    if not text or not text.strip(): return text
    aw=_ayah_words(); inv=_word_index()
    wo=text.split(); wn=[_norm(w) for w in wo]; n=len(wo)
    i=0; out=[]; buf=[]; last=None
    while i<n:
        best=None
        for (ai,pos) in inv.get(wn[i],()):
            words=aw[ai][1]; r=0; j=i; p=pos
            while j<n and p<len(words) and _weq(wn[j],words[p]): r+=1; j+=1; p+=1
            if best is None or r>best[1]: best=(ai,r)
        if best and best[1]>=min_run:
            code=aw[best[0]][0]
            if buf: out.append(("t"," ".join(buf))); buf=[]
            if last!=code: out.append(("q",code)); last=code
            i+=best[1]
        else:
            buf.append(wo[i]); last=None; i+=1
    if buf: out.append(("t"," ".join(buf)))
    res=[]
    for typ,val in out:
        if typ=="q":
            d=ayah_diac(val) or ""
            if d: res.append(("﴿"+d+"﴾") if mark else d)
        elif val.strip(): res.append(val)
    return " ".join(res).strip() or text
