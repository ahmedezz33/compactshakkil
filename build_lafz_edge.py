# -*- coding: utf-8 -*-
"""build_lafz_edge.py — يبني مقاطعَ لفظ الجلالة (رفع/جرّ/نصب/وقف) بمحرّك edge
معزولةً (نطقٌ صحيح) وبنفس صوت القراءة، لتُسبَك بلا فرق صوت. يُشغَّل مرّةً."""
import os, sys, subprocess, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, soundfile as sf
import tts_engine
sys.stdout.reconfigure(encoding="utf-8")

ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,"recordings","lafz"); os.makedirs(OUT,exist_ok=True)
REAL=os.path.join(ROOT,"recordings","lafz_real")
CASES={"nom":"اللَّهُ","gen":"اللَّهِ","acc":"اللَّهَ","waqf":"اللَّهْ"}
SR=24000

def _ffmpeg():
    for c in (os.path.join(ROOT,"venv","Scripts","ffmpeg.exe"), shutil.which("ffmpeg")):
        if c and os.path.exists(c): return c
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: return "ffmpeg"

def _to_wav(src):
    tmp=tempfile.mktemp(suffix=".wav")
    subprocess.run([_ffmpeg(),"-y","-loglevel","error","-i",src,"-ac","1","-ar",str(SR),tmp],check=True)
    x,_=sf.read(tmp,dtype="float32")
    try: os.remove(tmp)
    except Exception: pass
    return x

def _trim(x,thr=0.02):
    idx=np.where(np.abs(x)>thr)[0]
    if len(idx)==0: return x
    a=max(0,idx[0]-int(SR*0.01)); b=min(len(x),idx[-1]+int(SR*0.02))
    return x[a:b]

def _fade(x,ms=12):
    n=int(SR*ms/1000)
    if n>0 and len(x)>2*n:
        x[:n]*=np.linspace(0,1,n); x[-n:]*=np.linspace(1,0,n)
    return x

# احفظ نسخةَ المقاطع الحقيقيّة مرّةً قبل الاستبدال
if not os.path.isdir(REAL):
    os.makedirs(REAL,exist_ok=True)
    for fn in os.listdir(OUT):
        if fn.endswith(".wav"): shutil.copy(os.path.join(OUT,fn), os.path.join(REAL,fn))
    print("backed up real clips ->",REAL)

voice=tts_engine.default_voice(); print("voice:",voice)
for tag,word in CASES.items():
    try:
        p,eng=tts_engine.synthesize(word, voice=voice, rate_pct=-10, word_gap=0, use_cache=False)
        x=_fade(_trim(_to_wav(p)))
        pk=float(np.max(np.abs(x))) or 1.0; x=x/pk*0.92
        sf.write(os.path.join(OUT,tag+".wav"), x, SR, subtype="PCM_16")
        print(f"  OK {tag:4} '{word}' dur={len(x)/SR:.2f}s eng={eng}")
    except Exception as e:
        import traceback; print("  ERR",tag,e); traceback.print_exc()
print("DONE ->",OUT)
