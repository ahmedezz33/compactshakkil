# -*- coding: utf-8 -*-
"""
lafz_splice.py — يسبكُ مقطعَ لفظ الجلالة «الله» الحقيقيَّ (تلاوةُ المنشاوي) داخل
قراءة edge للنصوص غير القرآنيّة: كلُّ ما ليس «الله» يقرؤه edge، و«الله» بصوتٍ
حقيقيٍّ مطابقٍ لحالتها الإعرابيّة (نُصب/جرّ/رفع) من recordings/lafz/.
آمِن: إن نقصت المقاطعُ أو حدث خطأ يرجع None فيقرأ edge كامل النصّ.
"""
import os, re, sys, wave, subprocess, tempfile, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import soundfile as sf
import tts_engine

ROOT=os.path.dirname(os.path.abspath(__file__))
LAFZ=os.path.join(ROOT,"recordings","lafz")
FATHA,DAMMA,KASRA,SUKUN="َ","ُ","ِ","ْ"

def _ffmpeg():
    import shutil
    for c in (os.path.join(ROOT,"venv","Scripts","ffmpeg.exe"), shutil.which("ffmpeg")):
        if c and os.path.exists(c): return c
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: return "ffmpeg"

def _norm(w):
    w="".join(c for c in w if not unicodedata.combining(c))
    return w.translate(str.maketrans({"ٱ":"ا","أ":"ا","إ":"ا","آ":"ا"}))

def is_lafz(tok):
    """كلمةٌ = لفظُ الجلالة مجرّدةً (بلا سابقةٍ ملتصقة كـ«لله/والله/بالله»)."""
    core=_norm(tok).strip("،.:؛!؟\"'()")
    return core=="الله"

def _case_tag(tok):
    for ch in reversed(tok):
        if ch==DAMMA: return "nom"
        if ch==KASRA: return "gen"
        if ch==FATHA: return "acc"
        if ch==SUKUN: return "waqf"
    return "nom"

def clip_for(tok):
    tag=_case_tag(tok)
    order={"nom":["nom","nom2","gen","acc"],"gen":["gen","gen2","nom","acc"],
           "acc":["acc","acc2","gen","nom"],"waqf":["waqf","gen","nom","acc"]}[tag]
    for t in order:
        p=os.path.join(LAFZ,t+".wav")
        if os.path.exists(p): return p
    return None

def available():
    # مُعطَّلٌ افتراضيًّا: اللصقُ يُحدِثُ سكوتًا وخيطَ وصل. فعِّلْه بـ LAFZ_SPLICE=1 عند الحاجة.
    if os.environ.get("LAFZ_SPLICE","0")!="1": return False
    return any(os.path.exists(os.path.join(LAFZ,t+".wav")) for t in ("nom","gen","acc"))

def _read_any(path, sr):
    """اقرأ أيَّ ملفٍّ (mp3/wav) → مصفوفةُ مونو float32 عند معدّل sr عبر ffmpeg."""
    tmp=tempfile.mktemp(suffix=".wav")
    subprocess.run([_ffmpeg(),"-y","-loglevel","error","-i",path,"-ac","1","-ar",str(sr),tmp],
                   check=True)
    x,_=sf.read(tmp,dtype="float32")
    try: os.remove(tmp)
    except Exception: pass
    return x

def _peak(x, lvl=0.89):
    pk=float(np.max(np.abs(x))) if len(x) else 0.0
    return (x/pk*lvl) if pk>1e-6 else x

def read_with_lafz(dia_text, mode="waqf", edge_prepare=None, voice=None, rate_pct=-10):
    """يرجع مسارَ wav مسبوكًا، أو None لو لا داعي/تعذّر (فيتولّى edge كاملًا)."""
    if not available() or not dia_text or not dia_text.strip(): return None
    toks=dia_text.split()
    if not any(is_lafz(t) for t in toks): return None
    if edge_prepare is None:
        from pronounce import edge_prepare
    voice=voice or tts_engine.default_voice()
    SR=24000
    # segments: ('edge', "نص") أو ('lafz', clip_path)
    segs=[]; run=[]
    for t in toks:
        if is_lafz(t):
            if run: segs.append(("edge"," ".join(run))); run=[]
            cp=clip_for(t)
            segs.append(("lafz",cp) if cp else ("edge",t))
        else: run.append(t)
    if run: segs.append(("edge"," ".join(run)))
    pieces=[]; gap=np.zeros(int(SR*0.006),dtype=np.float32)
    last=len(segs)-1
    for i,(kind,val) in enumerate(segs):
        try:
            if kind=="edge":
                # المقاطعُ قبل «الله» تُنطَقُ وصلًا (تدفّقٌ بلا وقفة)؛ الأخيرُ فقط بالوضع المطلوب
                seg_mode=("wasl" if str(mode).startswith("wasl") else "waqf") if i==last else "wasl"
                spoken=edge_prepare(val, mode=seg_mode)
                p,_=tts_engine.synthesize(spoken, voice=voice, rate_pct=rate_pct, word_gap=0)
                if not p: continue
                x=_peak(_read_any(p,SR))
            else:
                x=_peak(_read_any(val,SR),0.95)   # لفظُ الجلالة أوضحُ قليلًا
            if len(x):
                pieces.append(x)
                if i!=last: pieces.append(gap)
        except Exception as e:
            print("lafz seg err:",kind,e)
    if not pieces: return None
    out=np.concatenate(pieces).astype(np.float32)
    op=os.path.join(tempfile.gettempdir(), "lafz_read.wav")
    sf.write(op,out,SR,subtype="PCM_16")
    return op
