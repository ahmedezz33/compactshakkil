# -*- coding: utf-8 -*-
"""
tts_engine.py — محرّكُ نطقٍ متعدّدُ الأصوات.

المحرّك الأساسيّ: edge-tts (أصواتٌ عصبيّةٌ من مايكروسوفت، مجّانيّة، بلا مفتاح،
عربيّةٌ كثيرةٌ ذكورًا وإناثًا ولهجاتٍ متعدّدة، مع ضبط السرعة والطبقة).
احتياطيّ: gTTS (صوتٌ واحد) إن لم يتوفّر edge-tts أو تعذّرت الشبكة.

  pip install edge-tts gtts

يقرأ النصَّ بعد تصحيح لفظ الجلالة وتطبيق الوقف (pronounce.tts_prepare).
"""
import asyncio, tempfile, os, shutil, subprocess, sys

# قائمةٌ منسّقةٌ احتياطيّة (تُستبدَل بالقائمة الحيّة إن نجح الجلب)
_FALLBACK=[
    ("السعوديّة — حامد (ذكر)","ar-SA-HamedNeural"),
    ("السعوديّة — زارية (أنثى)","ar-SA-ZariyahNeural"),
    ("مصر — شاكر (ذكر)","ar-EG-ShakirNeural"),
    ("مصر — سلمى (أنثى)","ar-EG-SalmaNeural"),
    ("الإمارات — حمدان (ذكر)","ar-AE-HamdanNeural"),
    ("الإمارات — فاطمة (أنثى)","ar-AE-FatimaNeural"),
    ("الأردن — تيم (ذكر)","ar-JO-TaimNeural"),
    ("الأردن — سناء (أنثى)","ar-JO-SanaNeural"),
    ("العراق — باسل (ذكر)","ar-IQ-BasselNeural"),
    ("الكويت — فهد (ذكر)","ar-KW-FahedNeural"),
    ("لبنان — رامي (ذكر)","ar-LB-RamiNeural"),
    ("سوريا — ليث (ذكر)","ar-SY-LaithNeural"),
    ("المغرب — جمال (ذكر)","ar-MA-JamalNeural"),
    ("الجزائر — إسماعيل (ذكر)","ar-DZ-IsmaelNeural"),
    ("قطر — معاذ (ذكر)","ar-QA-MoazNeural"),
    ("البحرين — علي (ذكر)","ar-BH-AliNeural"),
    ("ليبيا — عمر (ذكر)","ar-LY-OmarNeural"),
    ("عُمان — عبد الله (ذكر)","ar-OM-AbdullahNeural"),
    ("تونس — هادي (ذكر)","ar-TN-HediNeural"),
    ("اليمن — صالح (ذكر)","ar-YE-SalehNeural"),
    ("gTTS — صوت جوجل (احتياطيّ)","__gtts__"),
]

def _gender_ar(g):
    return {"Male":"ذكر","Female":"أنثى"}.get(g,g or "")

# ── espeak-ng: محرّكٌ صوتيٌّ أمينٌ يحترم التشكيلَ حرفيًّا (آليُّ الصوت) ──
_ESPEAK_PATHS=(r"C:\Program Files\eSpeak NG\espeak-ng.exe",
               r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe")
def espeak_bin():
    for c in ("espeak-ng","espeak"):
        p=shutil.which(c)
        if p: return p
    for p in _ESPEAK_PATHS:
        if os.path.exists(p): return p
    return None
def espeak_available(): return espeak_bin() is not None

# ── Piper: محرّكٌ عصبيٌّ محلّيّ (خاصّ، بلا إنترنت) يحترم التشكيلَ عبر espeak داخليًّا ──
def piper_model():
    """أوّلُ نموذج .onnx في مجلّد voices/ (يُفضَّل ar_JO-kareem)."""
    d=os.path.join(os.getcwd(),"voices")
    if not os.path.isdir(d): return None
    cands=[f for f in os.listdir(d) if f.endswith(".onnx")]
    if not cands: return None
    cands.sort(key=lambda f:(0 if "kareem-medium" in f else 1 if "kareem" in f else 2, f))
    return os.path.join(d,cands[0])
def piper_available(): return piper_model() is not None
def _piper_bin():
    """برنامجُ Piper: من PATH، أو نسخةٌ محمولةٌ محلّيّة (piper/piper.exe)، أو وحدةُ بايثون."""
    p=shutil.which("piper")
    if p: return [p]
    for cand in (os.path.join(os.getcwd(),"piper","piper.exe"),
                 os.path.join(os.getcwd(),"piper","piper"),
                 os.path.join(os.getcwd(),"piper.exe")):
        if os.path.exists(cand): return [cand]
    return [sys.executable,"-m","piper"]
def _piper_save(text, out):
    m=piper_model()
    if not m: raise RuntimeError("لا صوت Piper في voices/")
    cfg=m+".json"
    # piper 1.8.0: مرّرِ النصَّ كوسيطٍ مباشر (يتفادى مشكلةَ ترميزِ stdin على ويندوز)
    cmd=_piper_bin()+["--model",m]
    if os.path.exists(cfg): cmd+=["--config",cfg]
    cmd+=["--output_file",out, text]
    env=os.environ.copy(); env["PYTHONUTF8"]="1"; env["PYTHONIOENCODING"]="utf-8"
    r=subprocess.run(cmd, capture_output=True, timeout=180, env=env)
    if r.returncode!=0 or not (os.path.exists(out) and os.path.getsize(out)>44):
        # احتياط: أعِدْ عبر stdin مع UTF-8
        r2=subprocess.run(_piper_bin()+["--model",m,"--output_file",out],
                          input=text.encode("utf-8"), capture_output=True, timeout=180, env=env)
        if not (os.path.exists(out) and os.path.getsize(out)>44):
            raise RuntimeError("piper أنتجَ ملفًّا فارغًا: "+(r.stderr or b"").decode("utf-8","replace")[:300])


def piper_raw_available():
    """هل مسارُ الـ phoneme الخام جاهز (صوت + onnxruntime)؟"""
    if not piper_available(): return False
    try:
        import piper_raw; return piper_raw.available()
    except Exception: return False

def piper_phonemes_save(ipa, out):
    """نطقُ Piper من IPA خامٍ مباشرةً — يحترمُ التفخيم/الترقيق واللامَ الشمسيّة.
    يرمي استثناءً إن تعذّر (فيرجعُ المتّصِلُ إلى المسار النصّيّ)."""
    m=piper_model()
    if not m: raise RuntimeError("لا صوت Piper في voices/")
    import piper_raw
    if not piper_raw.available():
        raise RuntimeError("onnxruntime غير مثبَّت (pip install onnxruntime)")
    return piper_raw.synth(ipa, m, out)

def default_voice_id():
    """صوتُ edge الافتراضيّ (Piper مُعطَّلٌ حاليًّا)."""
    return default_voice()

def _espeak_save(text, out, rate_pct=0, pitch_hz=0, gap=0):
    binp=espeak_bin()
    if not binp: raise RuntimeError("espeak-ng غير مثبَّت")
    wpm=max(70,min(300,int(150*(1+rate_pct/100.0))))
    pit=max(0,min(99,int(50+pitch_hz)))
    # نقرأ النصَّ من ملفٍّ (UTF-8) لا من سطر الأوامر: يتفادى القطعَ ومشاكلَ الترميز
    txt=os.path.splitext(out)[0]+".txt"
    with open(txt,"w",encoding="utf-8") as f: f.write(text)
    cmd=[binp,"-v","ar","-s",str(wpm),"-p",str(pit)]
    if gap>0: cmd+=["-g",str(int(gap))]        # فجوةٌ بين الكلمات (وحدات 10ملّي ثانية)
    cmd+=["-w",out,"-f",txt]
    subprocess.run(cmd, check=True, timeout=120)

def list_voices():
    """أرجِع [(تسمية, معرّف)] لكلّ الأصوات العربيّة — حيًّا إن أمكن، وإلّا الاحتياطيّة."""
    try:
        import edge_tts
        vs=asyncio.run(edge_tts.list_voices())
        ar=[v for v in vs if v.get("Locale","").startswith("ar")]
        if not ar: raise RuntimeError("لا أصوات عربيّة")
        ar.sort(key=lambda v:(v["Locale"],v["ShortName"]))
        out=[]
        for v in ar:
            loc=v["Locale"]; sn=v["ShortName"]
            name=sn.split("-")[-1].replace("Neural","")
            out.append((f"{loc} — {name} ({_gender_ar(v.get('Gender'))})", sn))
        out.append(("gTTS — صوت جوجل (احتياطيّ)","__gtts__"))
        return _with_espeak(out)
    except Exception as e:
        print("⚠️ تعذّر جلبُ قائمة أصوات edge-tts؛ استعمالُ القائمة الاحتياطيّة:", e)
        return _with_espeak(list(_FALLBACK))

def f5_available(): return False    # استُبعِد F5 (جودةٌ رديئة)
def _f5_available_old():
    try:
        import f5_engine; return f5_engine.available()
    except Exception: return False

def _with_espeak(lst):
    """يُضيف F5 العربيّ (عصبيّ SOTA) ثمّ Piper إن وُجدا، ثمّ espeak إن توفّر."""
    if f5_available():
        import f5_engine
        _lbl=("Arabic F5-TTS — المنشاويّ المصقول (عصبيّ، أمينٌ للتشكيل، GPU)"
              if f5_engine.is_finetuned() else
              "Arabic F5-TTS (عصبيّ SOTA — أمينٌ للتشكيل، GPU)")
        lst=lst+[(_lbl,"__f5__")]
    if piper_available():
        lst=lst+[("Piper محلّيّ (عصبيّ — أمينٌ للتشكيل، بلا إنترنت)","__piper__")]
    if espeak_available():
        lst=lst+[("espeak-ng (آليّ — أمينٌ للتشكيل، جودةٌ أقلّ)","__espeak__")]
    return lst

def default_voice():
    return "ar-SA-HamedNeural"

def _edge_save(text, voice, rate, pitch, out):
    import edge_tts
    async def go():
        c=edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await c.save(out)
    asyncio.run(go())

def _gtts_save(text, out):
    from gtts import gTTS
    gTTS(text, lang="ar").save(out)

def _space_out(text):
    """أدرِج فاصلةً بين الكلمات لإجبار المحرّكات العصبيّة على التمهّل بينها."""
    out=[]
    for line in text.split("\n"):
        out.append(" ، ".join(w for w in line.split(" ") if w))
    return "\n".join(out)

# ── طبقةُ تخزينِ الأصوات محلّيًّا (cache) ───────────────────────────────
# أوّلُ توليدٍ لنصٍّ+صوتٍ يُجلَب من الخادم ويُخزَّن في recordings/tts_cache/؛ وأيُّ
# طلبٍ مطابقٍ بعده يُشغَّل محلّيًّا فورًا وبلا إنترنت. المفتاحُ يشمل النصَّ المُغذَّى
# والصوتَ والسرعةَ والطبقةَ والتمهّل، فأيُّ تغييرٍ يُنشئ مدخلًا جديدًا تلقائيًّا.
import hashlib
CACHE_DIR=os.path.join("recordings","tts_cache")
_LABELS={"piper":"Piper محلّيّ (عصبيّ، يحترم التشكيل)",
         "espeak":"espeak-ng (نطقٌ أمينٌ للتشكيل)",
         "gtts":"gTTS (يتجاهل التشكيل غالبًا)",
         "edge":"edge-tts"}
def _cache_key(parts):
    raw="\x1f".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def cache_stats():
    """عددُ المقاطع المخزَّنة وحجمُها (لعرضه في التطبيق)."""
    try:
        fs=[f for f in os.listdir(CACHE_DIR) if not f.endswith(".tmp")]
        sz=sum(os.path.getsize(os.path.join(CACHE_DIR,f)) for f in fs)
        return len(fs), sz
    except Exception: return 0,0

def clear_cache():
    """يُفرِغ الذاكرةَ المحلّيّة (يعيد التوليدَ من الخادم لاحقًا)."""
    n=0
    try:
        for f in os.listdir(CACHE_DIR):
            try: os.remove(os.path.join(CACHE_DIR,f)); n+=1
            except Exception: pass
    except Exception: pass
    return n

def synthesize(text, voice=None, rate_pct=0, pitch_hz=0, out=None, word_gap=0, use_cache=True):
    """
    نطقُ النصّ إلى ملفّ وإرجاعُ (المسار، اسمُ المحرّك الذي أنتجه فعلًا).
      voice     : معرّف صوت edge-tts (مثل ar-SA-HamedNeural) أو '__gtts__' أو '' للافتراضيّ.
      rate_pct  : سرعةٌ نسبيّة (%)، مثلاً -20 أبطأ، +20 أسرع.
      pitch_hz  : طبقةُ الصوت (Hz)، مثلاً -20 أخفض، +20 أعلى.
      use_cache : خزِّن الناتجَ محلّيًّا وأعِد استعمالَه للطلب المطابق (بلا إنترنت).
    """
    if not text or not text.strip(): return None, "—"
    voice=(voice or "").strip() or default_voice()
    # حدّد المحرّكَ والامتدادَ ومفتاحَ الذاكرة
    if   voice=="__f5__":
        import f5_engine
        _ra,_rt=f5_engine._reference()
        eng,ext,kp="f5","wav",("f5",text,_ra,_rt,       # المفتاحُ يشمل المرجعَ والإعداداتِ والنموذج
                               f5_engine.NFE_STEP,f5_engine.CFG_STRENGTH,f5_engine.SPEED,
                               "ft" if f5_engine.is_finetuned() else "base")
    elif voice=="__piper__":  eng,ext,kp="piper","wav",("piper",text)
    elif voice=="__espeak__": eng,ext,kp="espeak","wav",("espeak",text,rate_pct,pitch_hz,word_gap)
    elif voice=="__gtts__":   eng,ext,kp="gtts","mp3",("gtts",text,word_gap)
    else:                     eng,ext,kp="edge","mp3",("edge",voice,text,rate_pct,pitch_hz,word_gap)

    # إصابةُ الذاكرة → تشغيلٌ محلّيٌّ فوريّ
    cpath=None
    if use_cache:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            cpath=os.path.join(CACHE_DIR, _cache_key(kp)+"."+ext)
            if os.path.exists(cpath) and os.path.getsize(cpath)>0:
                lbl=_LABELS[eng]+(f" ({voice})" if eng=="edge" else "")
                return cpath, lbl+" ⚡ (من الذاكرة المحلّيّة)"
        except Exception: cpath=None

    # ولّد إلى مؤقّتٍ ثمّ انقُله ذرّيًّا (لئلّا يُخزَّن ملفٌّ ناقص)
    tmp=(cpath+".tmp") if cpath else (out or os.path.join(tempfile.gettempdir(),"tts_out."+ext))
    def _finish(label):
        if cpath:
            try: os.replace(tmp, cpath); return cpath, label
            except Exception: return tmp, label
        return tmp, label

    if eng=="f5":
        import f5_engine
        f5_engine.synth(text, out=tmp); return _finish("Arabic F5-TTS (عصبيّ SOTA — أمينٌ للتشكيل)")
    if eng=="piper":
        try:
            _piper_save(text,tmp); return _finish("Piper محلّيّ (عصبيّ، يحترم التشكيل)")
        except Exception as e:
            print("⚠️ Piper فشل؛ الرجوعُ إلى edge:", e)
            try:
                if os.path.exists(tmp): os.remove(tmp)
            except Exception: pass
            return synthesize(text, default_voice(), rate_pct, pitch_hz, out, word_gap, use_cache)
    if eng=="espeak":
        _espeak_save(text,tmp,rate_pct,pitch_hz,gap=word_gap); return _finish(_LABELS["espeak"])

    gen=_space_out(text) if word_gap>0 else text     # تمهّلٌ بين الكلمات (edge/gTTS)
    if eng=="gtts":
        _gtts_save(gen,tmp); return _finish(_LABELS["gtts"])
    rate=f"{'+' if rate_pct>=0 else ''}{int(rate_pct)}%"
    pitch=f"{'+' if pitch_hz>=0 else ''}{int(pitch_hz)}Hz"
    try:
        _edge_save(gen,voice,rate,pitch,tmp); return _finish(f"edge-tts ({voice})")
    except Exception as e:
        print("⚠️ edge-tts فشل؛ الرجوعُ إلى gTTS:", e)
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception: pass
        # لا نُخزّن البديلَ تحت مفتاح edge — أخرِجه لمؤقّتٍ عاديّ
        fb=out or os.path.join(tempfile.gettempdir(),"tts_out.mp3")
        _gtts_save(gen,fb); return fb, f"gTTS (edge-tts غير متاح: {type(e).__name__})"
