# -*- coding: utf-8 -*-
"""make_lesson_video.py — مولّدُ فيديوهاتٍ تعليميّةٍ للنطق (نموذجٌ أوّليّ).
بطاقةٌ لكلِّ كلمة: الكلمةُ المشكولةُ كبيرةً + نقحرتُها اللاتينيّةُ + صوتُها.
التزامنُ مضمونٌ: مدّةُ كلِّ بطاقةٍ = مدّةُ صوتِ كلمتِها (تُقاسُ من wav).
يعملُ على جهازِ المالك. يُشكّلُ العربيّةَ بـarabic_reshaper+bidi (بلا حاجةٍ لـlibraqm).

  python make_lesson_video.py --text "ذهب الطالب إلى المدرسة" --out lesson.mp4
"""
import os, sys, argparse, tempfile, subprocess, shutil, wave
BASE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE,"scripts")); sys.path.insert(0, BASE)
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass

# ── تشكيلُ العربيّةِ للرسمِ بلا libraqm (يُبقي الحركات) ──
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _RS=arabic_reshaper.ArabicReshaper({'delete_harakat': False, 'support_ligatures': True})
    def shape(t): 
        try: return get_display(_RS.reshape(t))
        except Exception: return t
    HAS_SHAPE=True
except Exception as e:
    def shape(t): return t
    HAS_SHAPE=False
    print("تنبيه: arabic_reshaper/bidi غيرُ متاحٍ — قد تظهرُ العربيّةُ مفكّكةً. ثبّتْ: pip install arabic-reshaper python-bidi")

def ffmpeg_bin():
    p=os.path.join(BASE,"venv","Scripts","ffmpeg.exe")
    return p if os.path.exists(p) else (shutil.which("ffmpeg") or "ffmpeg")
FFMPEG=ffmpeg_bin()

def run(cmd):
    r=subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode!=0: raise RuntimeError("ffmpeg: "+r.stderr.decode("utf-8","replace")[-400:])

def to_wav(src, dst, gap, sr=24000):
    run([FFMPEG,"-y","-i",src,"-ar",str(sr),"-ac","1","-af",f"apad=pad_dur={gap}",dst])
def silence(dst, dur, sr=24000):
    run([FFMPEG,"-y","-f","lavfi","-i",f"anullsrc=r={sr}:cl=mono","-t",f"{dur}",dst])
def wav_dur(path):
    with wave.open(path,"rb") as w: return w.getnframes()/float(w.getframerate())

def _tw(draw, s, font):
    bb=draw.textbbox((0,0), s, font=font); return bb[2]-bb[0]

def fit_font(draw, shaped, font_path, max_w, start=150, lo=28):
    from PIL import ImageFont
    s=start
    while s>lo:
        f=ImageFont.truetype(font_path,s)
        if _tw(draw, shaped, f)<=max_w: return f
        s-=6
    return ImageFont.truetype(font_path,lo)

def wrap_lines(draw, text, font, max_w):
    words=text.split(" "); lines=[]; cur=""
    for w in words:
        cand=(cur+" "+w).strip()
        if _tw(draw, shape(cand), font)>max_w and cur: lines.append(cur); cur=w
        else: cur=cand
    if cur: lines.append(cur)
    return lines

def card(path, word_ar, latin, idx, total, W, H, font_path):
    from PIL import Image, ImageDraw, ImageFont
    BG=(250,247,240); FG=(22,22,28); ACC=(176,42,42); SUB=(90,90,96)
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img)
    hf=ImageFont.truetype(font_path,40)
    d.text((W//2, int(H*0.12)), shape("تعلّمِ النطقَ"), font=hf, fill=SUB, anchor="mm")
    d.text((int(W*0.06), int(H*0.12)), f"{idx}/{total}", font=ImageFont.truetype(font_path,36), fill=SUB, anchor="lm")
    sw=shape(word_ar)
    bf=fit_font(d, sw, font_path, int(W*0.86), start=160)
    d.text((W//2, int(H*0.45)), sw, font=bf, fill=ACC, anchor="mm")
    if latin:
        d.text((W//2, int(H*0.72)), latin, font=ImageFont.truetype(font_path,56), fill=FG, anchor="mm")
    img.save(path,"PNG")

def title_card(path, text_ar, W, H, font_path):
    from PIL import Image, ImageDraw, ImageFont
    BG=(15,18,38); FG=(240,240,245)
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img)
    f=ImageFont.truetype(font_path,64)
    lines=wrap_lines(d, text_ar, f, int(W*0.86))
    lh=int(64*1.7); y=H//2-(len(lines)*lh)//2
    for ln in lines:
        d.text((W//2, y), shape(ln), font=f, fill=FG, anchor="mm"); y+=lh
    img.save(path,"PNG")

import re as _re
_HRK=_re.compile(r"[\u064B-\u0652\u0670\u0640]")
def _strip_marks(s): return _HRK.sub("", s)

def _edge_marks(text, voice, mp3_out, rate_pct=0):
    """تركيبٌ متّصلٌ للجملةِ كاملةً عبرَ edge-tts، مع إرجاعِ بداياتِ الكلمات (ثوانٍ)."""
    import asyncio, edge_tts
    rate=f"{int(rate_pct):+d}%"
    async def go():
        comm=edge_tts.Communicate(text, voice, rate=rate)
        audio=b""; starts=[]
        async for ch in comm.stream():
            if ch["type"]=="audio": audio+=ch["data"]
            elif ch["type"]=="WordBoundary": starts.append(ch["offset"]/1e7)
        return audio, starts
    audio, starts = asyncio.run(go())
    if not audio: raise RuntimeError("edge: لا صوت")
    open(mp3_out,"wb").write(audio)
    return starts

def generate(text, out="lesson.mp4", font=None, voice=None, mode="waqf",
             w=1280, h=720, rate_pct=0, intro=3.0, fps=25, show_latin=True, log=print):
    font=font or os.path.join(BASE,"data","fonts","Amiri-Bold.ttf")
    text=(text or "").strip()
    if not text: raise ValueError("لا نصّ.")
    if not os.path.exists(font): raise ValueError(f"الخطُّ غيرُ موجود: {font}")
    import diac_pipeline, tts_engine
    try: import g2p; HAS_G2P=True
    except Exception as e: log(f"تنبيه g2p: {e}"); HAS_G2P=False
    try: from pronounce import edge_prepare
    except Exception: edge_prepare=None
    dia=(diac_pipeline.diacritize(text, True)[0] or text)
    words=[x for x in dia.split() if x.strip()]; k=len(words)
    log(f"النصُّ المشكول: {dia}"); log(f"عددُ الكلمات: {k} · تشكيلُ العرض: {'نعم' if HAS_SHAPE else 'لا'}")
    voice=voice or tts_engine.default_voice()
    work=tempfile.mkdtemp(prefix="lesson_")
    def wp(n): return os.path.join(work,n).replace("\\","/")
    # نصُّ النطقِ كما في CompactShakkil (edge_prepare على المشكول)
    spoken=dia
    if edge_prepare:
        try: spoken=edge_prepare(dia, mode) or dia
        except Exception: spoken=dia
    speech=wp("speech.wav"); starts=None
    is_edge=bool(voice) and not voice.startswith("__")
    if is_edge:
        try:
            mp3=wp("speech.mp3"); marks=_edge_marks(spoken, voice, mp3, rate_pct)
            to_wav(mp3, speech, 0.0)
            if k>0 and len(marks)>=k: starts=marks[:k]
            elif k>0 and len(marks)>0: starts=(marks+[marks[-1]]*k)[:k]
            log(f"صوتٌ متّصلٌ (edge) + توقيتُ {len(marks)} كلمة")
        except Exception as e:
            log(f"تعذّر مسارُ edge المتزامن ({e}) — تركيبٌ كاملٌ بديل."); is_edge=False
    if not is_edge or starts is None:
        raw,_=tts_engine.synthesize(spoken, voice=voice, rate_pct=rate_pct, word_gap=0)
        to_wav(raw, speech, 0.0); starts=None
    sdur=wav_dur(speech)
    if starts is None:                       # توقيتٌ تناسبيٌّ بطولِ الحروف
        lens=[max(1,len(_strip_marks(x))) for x in words]; tot=sum(lens) or 1; acc=0; starts=[]
        for L in lens: starts.append(sdur*acc/tot); acc+=L
    bounds=[0.0]+[starts[i] for i in range(1,k)]+[sdur]
    # صوتٌ نهائيّ = صمتُ المقدّمة + الكلامُ المتّصل
    sil=wp("intro.wav"); silence(sil, intro)
    at=wp("a.txt"); open(at,"w",encoding="utf-8").write(f"file '{sil}'\nfile '{speech}'\n")
    full=wp("full.wav"); run([FFMPEG,"-y","-f","concat","-safe","0","-i",at,"-c","copy",full])
    # الإطارات
    frames=[]; tcard=wp("intro.png"); title_card(tcard, dia, w, h, font); frames.append((tcard, intro))
    for i,word in enumerate(words):
        latin=""
        if HAS_G2P and show_latin:
            try: latin=g2p.phonemize(word, mode)[1].strip()
            except Exception: latin=""
        cf=wp(f"c{i:03d}.png"); card(cf, word, latin, i+1, k, w, h, font)
        dur=max(0.15, bounds[i+1]-bounds[i]); frames.append((cf, dur))
        log(f"  [{i+1}/{k}] {word}  ({latin})  {dur:.2f}s")
    ft=wp("frames.txt")
    with open(ft,"w",encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for p,d in frames: f.write(f"file '{p}'\nduration {d:.3f}\n")
        f.write(f"file '{frames[-1][0]}'\n")
    outp=os.path.abspath(out); os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
    run([FFMPEG,"-y","-f","concat","-safe","0","-i",ft,"-i",full,
         "-vf",f"fps={fps},format=yuv420p","-c:v","libx264","-c:a","aac","-shortest",outp])
    log(f"✅ الفيديو: {outp}"); return outp

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--text", default=""); ap.add_argument("--infile", default="")
    ap.add_argument("--out", default="lesson.mp4")
    ap.add_argument("--font", default=os.path.join(BASE,"data","fonts","Amiri-Bold.ttf"))
    ap.add_argument("--mode", default="waqf"); ap.add_argument("--voice", default="")
    ap.add_argument("--w", type=int, default=1280); ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--rate", type=int, default=0); ap.add_argument("--intro", type=float, default=3.0)
    ap.add_argument("--fps", type=int, default=25)
    a=ap.parse_args()
    text=(a.text.strip() or (open(a.infile,encoding="utf-8").read().strip() if a.infile else ""))
    generate(text, out=a.out, font=a.font, voice=(a.voice or None), mode=a.mode,
             w=a.w, h=a.h, rate_pct=a.rate, intro=a.intro, fps=a.fps)

if __name__=='__main__': main()
