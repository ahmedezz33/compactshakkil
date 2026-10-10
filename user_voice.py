# -*- coding: utf-8 -*-
"""
user_voice.py — مكتبةُ نطقٍ بصوت المستخدم.
يحفظ تسجيلاتِ المستخدم (أو ملفّاتٍ مرفوعة) مفهرسةً بالنصّ، ويُرجِعها عند الطلب
لتُشغَّل بدل صوت المحرّك. محلّيٌّ بالكامل في مجلّد recordings/.
"""
import os, json, hashlib, shutil
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from data.vocab_v2 import strip_diacritics

DIR="recordings"
IDX=os.path.join(DIR,"library.json")

def _norm(t):
    """مفتاحُ المطابقة: بلا حركاتٍ ولا مسافاتٍ زائدة (يطابق النصَّ مهما اختلف تشكيله)."""
    return " ".join(strip_diacritics(t or "").split())

def _load():
    try: return json.load(open(IDX,encoding="utf-8"))
    except Exception: return {}

def _save(d):
    os.makedirs(DIR,exist_ok=True)
    json.dump(d,open(IDX,"w",encoding="utf-8"),ensure_ascii=False,indent=1)

def save_recording(text, audio_path):
    """احفظ تسجيلَ المستخدم لهذا النصّ. audio_path: مسارٌ من gr.Audio (تسجيل أو رفع)."""
    if not text or not text.strip(): return "⚠️ أدخِل النصّ أوّلًا."
    if not audio_path or not os.path.exists(audio_path): return "⚠️ سجّل أو ارفع ملفًّا صوتيًّا أوّلًا."
    os.makedirs(DIR,exist_ok=True)
    k=_norm(text); h=hashlib.md5(k.encode("utf-8")).hexdigest()[:12]
    ext=os.path.splitext(audio_path)[1] or ".wav"
    dst=os.path.join(DIR,h+ext)
    shutil.copyfile(audio_path,dst)
    d=_load(); d[k]=os.path.basename(dst); _save(d)
    return f"✅ حُفِظ نطقُك لـ «{text.strip()}». سيُشغَّل تلقائيًّا في تبويب النطق."

def lookup(text):
    """أرجِع مسارَ تسجيل المستخدم لهذا النصّ إن وُجد، وإلّا None."""
    d=_load(); k=_norm(text)
    fn=d.get(k)
    if fn:
        p=os.path.join(DIR,fn)
        if os.path.exists(p): return p
    return None

def delete(text):
    d=_load(); k=_norm(text)
    if k in d:
        p=os.path.join(DIR,d[k])
        try:
            if os.path.exists(p): os.remove(p)
        except Exception: pass
        del d[k]; _save(d); return f"🗑️ حُذِف تسجيلُ «{text.strip()}»."
    return "لا يوجد تسجيلٌ محفوظٌ لهذا النصّ."

def list_saved():
    """قائمةُ النصوص المحفوظة."""
    return sorted(_load().keys())
