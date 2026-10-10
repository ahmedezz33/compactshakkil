# -*- coding: utf-8 -*-
"""
qaida_voice.py — مخزنُ وحداتِ القاعدة النورانيّة بصوت المستخدم + نطقٌ تركيبيّ.

الفكرة: كلُّ «وحدة» = حرفٌ بحركته (بَ، بُ، بْ، بّ…). تُسجَّل مرّةً بصوتك، ثمّ
يُقسَّم أيُّ نصٍّ إلى وحداته وتُركَّب المقاطعُ الصوتيّة لتُنطَق كاملةً بصوتك.
ما لم تُسجّله يُولّده Piper مؤقّتًا (WAV) حتى يكتمل النطق.
كلُّ الملفّات WAV (لدمجها بمكتبة wave القياسيّة بلا اعتمادات خارجيّة).
"""
import os, json, hashlib, wave, tempfile
try: import audioop
except Exception: audioop=None
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from pronounce import _units, SHADDA, FATHA, KASRA, DAMMA, SUKUN, FATHATAN, KASRATAN, DAMMATAN, DAGGER_ALIF
import tts_engine

DIR=os.path.join("recordings","units")
IDX=os.path.join("recordings","units.json")
_VOWELS=[FATHA,KASRA,DAMMA,SUKUN,FATHATAN,KASRATAN,DAMMATAN,DAGGER_ALIF]
RATE=22050

def unit_key(letter, marks):
    """مفتاحٌ قانونيّ: حرف + (شدّة إن وُجدت) + أوّل حركة — ليطابق التسجيلَ والتوليد."""
    v="".join(c for c in marks if c in _VOWELS)[:1]
    sh=SHADDA if SHADDA in marks else ""
    return letter+sh+v

def _load():
    try: return json.load(open(IDX,encoding="utf-8"))
    except Exception: return {}
def _save(d):
    os.makedirs(DIR,exist_ok=True)
    json.dump(d,open(IDX,"w",encoding="utf-8"),ensure_ascii=False,indent=1)

def save_unit(unit_text, audio_path):
    """احفظ تسجيلَ وحدةٍ (نصُّ الوحدة مثل «بَ»)."""
    if not unit_text or not unit_text.strip(): return "⚠️ اختر وحدةً أوّلًا."
    if not audio_path or not os.path.exists(audio_path): return "⚠️ سجّل الوحدةَ أوّلًا."
    u=_units(unit_text.strip())
    if not u: return "⚠️ وحدةٌ غير صالحة."
    k=ukey(unit_text)                 # المقطعُ كاملًا (يدعم المركّب «بَا/بُو/بِي»)
    os.makedirs(DIR,exist_ok=True)
    dst=os.path.join(DIR, hashlib.md5(k.encode("utf-8")).hexdigest()[:12]+".wav")
    try: _copy_as_wav(audio_path,dst)
    except Exception as e: return f"⚠️ يجب أن يكون التسجيلُ WAV. ({e})"
    d=_load(); d[k]=os.path.basename(dst); _save(d)
    return f"✅ حُفِظت الوحدة «{unit_text.strip()}» بصوتك."

def get_unit(letter, marks):
    d=_load(); k=unit_key(letter,marks); fn=d.get(k)
    if fn:
        p=os.path.join(DIR,fn)
        if os.path.exists(p): return p
    return None

def ukey(text):
    """مفتاحُ وحدةٍ مركّبةٍ (مقطعٌ كامل مثل «بَا/بُو/بِي») = نصُّها بلا تطويل."""
    return (text or "").replace("ـ","").strip()

def get_unit_text(text):
    d=_load(); fn=d.get(ukey(text))
    if fn:
        p=os.path.join(DIR,fn)
        if os.path.exists(p): return p
    return None

_SRCIDX=os.path.join("recordings","units_source.json")
def is_user(text):
    """هل الوحدةُ مسجَّلةٌ بصوت المستخدم (لا مولّدةٌ آليًّا)؟"""
    k=ukey(text)
    if k not in _load(): return False
    try: s=json.load(open(_SRCIDX,encoding="utf-8"))
    except Exception: s={}
    return s.get(k) != "tts"        # المولّدُ آليًّا مُعلَّمٌ tts؛ غيرُه صوتُك

# وحداتٌ خاصّةٌ كاملةُ الكلمة (لفظ الجلالة مفخّمًا/مرقّقًا) — مفاتيحُها ثابتة
SPECIAL={"JALH":"§jalalah_heavy","JALL":"§jalalah_light"}
def get_special(key):
    d=_load(); fn=d.get(key)
    if fn:
        p=os.path.join(DIR,fn)
        if os.path.exists(p): return p
    return None
def save_special(key, wav_path):
    """يُخزِّن وحدةً خاصّةً (WAV) بمفتاحٍ ثابت (للجلالة المفخّمة/المرقّقة)."""
    os.makedirs(DIR,exist_ok=True)
    dst=os.path.join(DIR, hashlib.md5(key.encode("utf-8")).hexdigest()[:12]+".wav")
    _copy_as_wav(wav_path,dst)
    d=_load(); d[key]=os.path.basename(dst); _save(d)
    return dst

def saved_units():
    return sorted(_load().keys())

# ── أدوات WAV (قياسيّة) ────────────────────────────────────────────────
def _copy_as_wav(src,dst):
    with wave.open(src,"rb") as w:      # يقبل WAV فقط
        data=_norm_frames(w);
    _write(dst,data)

def _norm_frames(w):
    nch,sw,fr,nf=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
    data=w.readframes(nf)
    if audioop is None: return data
    if sw!=2: data=audioop.lin2lin(data,sw,2); sw=2
    if nch==2: data=audioop.tomono(data,2,0.5,0.5)
    if fr!=RATE: data,_=audioop.ratecv(data,2,1,fr,RATE,None)
    return data

def _read_wav(path):
    with wave.open(path,"rb") as w: return _norm_frames(w)

def _write(path,frames):
    with wave.open(path,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(frames)

def _silence(ms):
    return b"\x00\x00"*int(RATE*ms/1000)

def _word_units(w, started):
    """وحداتُ كلمةٍ للتركيب: تُسقِط لامَ الشمسيّة الصامتة وألفَ الوصل/التعريف
    (وتُنطَق «أَ» في ابتداء العبارة فقط)، وتُبقي ألفَ المدّ. started: هل نُطِق
    شيءٌ قبلها في هذا السطر؟ يُرجِع (وحدات, started_جديد)."""
    u=_units(w); out=[]
    for i,(L,m) in enumerate(u):
        if L=="ل" and m=="" and i>0 and u[i-1][0]=="ا" and i+1<len(u):  # لامُ «الـ» الصامتة (ليست آخرَ الكلمة)
            continue
        if L=="ا" and m=="":
            if out and FATHATAN in out[-1][1]:   # ألفُ تنوين الفتح (مقعد) لا تُنطَق مدًّا
                started=True; continue
            nxt=u[i+1] if i+1<len(u) else None
            article = bool(nxt and nxt[0]=="ل" and nxt[1] in ("",SUKUN) and i+2<len(u))
            if i==0 or article:                  # ألفُ وصلٍ/تعريف
                if not started:
                    out.append(("أ",FATHA)); started=True   # تُنطَق «a» ابتداءً
                continue                          # وتُحذَف وصلًا
            out.append(("ا",""))                 # ألفُ مدٍّ ← تبقى
            started=True; continue
        if m=="" and L not in ("و","ي"):         # حرفٌ صامتٌ (وقفُ الآخِر) ← سكون
            out.append((L,SUKUN)); started=True; continue
        out.append((L,m)); started=True
    return out, started

_MADD=("ا","آ","ى")
def _tail(b, ms=170):
    """آخِرُ ms من صوتٍ (ذيلُ الحركة) لإطالة المدّ."""
    n=int(RATE*ms/1000)*2
    return b[-n:] if len(b)>n else b

def _is_madd(L,m):
    return L in _MADD or (L in ("و","ي") and m=="")

def _render_units(units):
    """يُركّب وحداتٍ: يُلصِق التضعيف (حرفان متماثلان) بلا فراغ، ويُنطِق المدَّ
    بإطالةِ حركةِ الوحدة السابقة نفسِها (لونٌ صحيحٌ: نُ→نوو، بَ→باا، بِ→بيي)
    بدل وحدةِ مدٍّ منفصلةٍ رديئة. يُرجِع (bytes, rec, tot, missing)."""
    fr=bytearray(); rec=0; tot=0; miss=[]; n=len(units); last=None
    i=0
    while i<n:
        L,m=units[i]
        # (١) وحدةٌ مركّبةٌ من القاعدة: حرفٌ محرّكٌ + حرفُ مدٍّ تالٍ (بَا/بُو/بِي) إن سُجِّلت
        if i+1<n and _is_madd(*units[i+1]) and not _is_madd(L,m):
            comp=L+m+units[i+1][0]
            p=get_unit_text(comp)
            if p:
                tot+=1; rec+=1
                try: b=_read_wav(p); fr+=b; last=b; fr+=_silence(22)
                except Exception: pass
                i+=2; continue
        # (٢) مدٌّ: أطِل ذيلَ الحركة السابقة (لونٌ صحيح) بدل وحدةِ مدٍّ منفصلة
        if _is_madd(L,m):
            tot+=1
            if last: rec+=1; fr+=_tail(last); fr+=_tail(last,120)
            else:
                p=get_unit("ا","")
                if p:
                    try: b=_read_wav(p); fr+=b; last=b; rec+=1
                    except Exception: pass
                else:
                    if (L+m) not in miss: miss.append(L+m)
                    fr+=_silence(120)
            i+=1; continue
        # (٣) وحدةٌ مفردة
        tot+=1; p=get_unit(L,m)
        nxtL=units[i+1][0] if i+1<n else None
        gap=0 if nxtL==L else 22               # حرفان متماثلان (شدّة) ← بلا فراغ
        if p:
            rec+=1
            try: b=_read_wav(p); fr+=b; last=b; fr+=_silence(gap)
            except Exception: pass
        else:
            if (L+m) not in miss: miss.append(L+m)
            fr+=_silence(120); last=None
        i+=1
    return bytes(fr),rec,tot,miss

def synth_text(text):
    """قسّم النصَّ إلى وحداتٍ وركّب تسجيلاتِك فقط (بلا Piper).
    أرجِع (مسار, عددُ المسجَّل, الكلّيّ, قائمةُ الوحدات الناقصة)."""
    if not text or not text.strip(): return None,0,0,[]
    frames=bytearray(); rec=0; tot=0; missing=[]
    from pronounce import jalalah_fallback
    def _merge(b,r,t,ms):
        nonlocal rec,tot
        frames.extend(b); rec+=r; tot+=t
        for u in ms:
            if u not in missing: missing.append(u)
    for line in text.split("\n"):
        started=False                              # ابتداءُ العبارة (لألف الوصل)
        for w in line.split(" "):
            if not w: continue
            if w in SPECIAL:                       # لفظُ الجلالة كوحدةٍ كاملة (ثقل/ترقيق)
                p=get_special(SPECIAL[w])
                if p:
                    tot+=1; rec+=1
                    try: frames.extend(_read_wav(p)); frames.extend(_silence(110))
                    except Exception: pass
                    started=True; continue
                fb=jalalah_fallback("heavy" if w=="JALH" else "light")  # احتياطيّ حرفيّ
                units,started=_word_units(fb, started)
                _merge(*_render_units(units)); frames.extend(_silence(110)); continue
            units,started=_word_units(w, started)
            _merge(*_render_units(units)); frames.extend(_silence(110))
    if not frames: return None,rec,tot,missing
    out=os.path.join(tempfile.gettempdir(),"qaida_concat.wav"); _write(out,bytes(frames))
    return out,rec,tot,missing
