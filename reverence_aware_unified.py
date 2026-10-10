# -*- coding: utf-8 -*-
"""
reverence_aware_unified.py — Reverence-Aware بنموذج واحد (V3-unified) + استرداد.

المبدأ (كما اتّفقنا): القرآن يبلغ 100% بالاسترداد الحرفيّ من الفهرس الموثوق،
لا بتدريب النموذج للكمال. النموذج العصبيّ الوحيد V3-unified للاحتياط فيما لا يُطابِق.

المستويات:
  1) آية تامّة        → استرداد النصّ الأصليّ (خطأ صفر = 100%)
  2) آية مضمّنة        → استرداد الآية
  3) مقطع من آية       → استرداد المقطع/الآية الحاوية
  4) محتوى قرآنيّ عابر  → V3-unified
  5) نصّ عامّ          → V3-unified
"""
import sys
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).parent))
from data.vocab_v2 import (VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID,
    split_letters_and_diacritics, merge_letters_and_diacritics, strip_diacritics, encode_chars)
from models.transformer import CompactShakkilBase

UNIFIED_CKPT = "compactshakkil_v3_unified/best_model.pt"   # أو outputs_v3_unified/latest.pt
QURAN_PATH = "data/raw/quran/quran-simple.txt"

import re
SMALL_ALIF = "ٰ"                 # الألف الخنجريّة (=ألف مدّ في الرسم البسيط)
TATWEEL = "ـ"
# توحيدُ الرسم العثمانيّ مع البسيط: صور الهمزة، والمقصورة، والتاء المربوطة،
# والألف الخنجريّة ← ألف. هكذا يطابِق «ٱلصَّٰلِحَٰتِ» ← «الصالحات»، «ءَامَنُوا» ← «آمنوا».
NORM_MAP = str.maketrans({
    "أ":"ا","إ":"ا","آ":"ا","ٱ":"ا",
    "ؤ":"و","ئ":"ي","ء":"",
    "ى":"ي","ة":"ه", SMALL_ALIF:"ا",
})
QSYM = set("۝۞ۣۖۗۘۙۚۛۜ۟۠ۡۢۤۥۦۧۨ۩۪ۭ۫")
_KEEP = re.compile(r"[^ء-ي ]")
_QMARKS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u06D6-\u06ED\u08D3-\u08FF]")
def _norm(s):
    """تطبيعٌ يوحّد الرسمَين ويُسقِط الأرقامَ والأقواسَ ورموزَ الوقف وأرقامَ الآي.
    نحذف العلاماتِ القرآنيّةَ الصغيرةَ حذفًا (لا نُبدِّلها فراغًا) لئلّا تنشقَّ الكلمةُ
    عند علامةٍ داخلها مثل «فِرَٰشًۭا» ← «فراش ا»؛ والخنجريّةُ والوصلةُ تتولّاهما NORM_MAP."""
    s = strip_diacritics(s).replace(TATWEEL, "")
    s = _QMARKS.sub("", s)
    s = s.translate(NORM_MAP)
    for _a,_b in (("صلواه","صلاه"),("زكواه","زكاه"),("حيواه","حياه"),
                  ("ربواا","ربا"),("مشكواه","مشكاه"),("غدواه","غداه"),
                  ("منواه","مناه"),("مرضاه","مرضاه")):
        s=s.replace(_a,_b)                 # توحيدُ الرسم العثمانيّ مع المجرّد
    return " ".join(_KEEP.sub(" ", s).split())

def _declean(orig):
    """يُزيل رموز الوقف (كتوكِنات) مع إبقاء التشكيل، فتحاذي كلماتُه التطبيعَ 1:1."""
    return " ".join(w for w in orig.split() if any(c not in QSYM for c in w))

def load_model(ckpt_path, device):
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    m = ckpt.get("config", {}).get("model", {})
    model = CompactShakkilBase(vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=m.get("d_model",256), nhead=m.get("nhead",8),
        num_encoder_layers=m.get("num_encoder_layers",4), dim_feedforward=m.get("dim_feedforward",1024),
        dropout=0.0, max_position=m.get("max_position",512), pad_id=PAD_ID).to(device)
    model.load_state_dict(ckpt["model_state"]); model.eval(); return model

@torch.no_grad()
def diacritize(text, model, device):
    letters,_=split_letters_and_diacritics(strip_diacritics(text))
    if not letters: return text
    ids=torch.tensor([encode_chars(letters)],dtype=torch.long,device=device)
    mask=torch.ones_like(ids,dtype=torch.bool)
    classes=model(ids,mask).argmax(dim=-1)[0].tolist()
    return merge_letters_and_diacritics(letters,classes)

BISM_NORM=_norm("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ")   # يُحسَب بالتطبيع نفسه (الرحمان)
def _read_edition(path):
    """أسطرُ آياتٍ نظيفةٌ: يتجاهل التعليقاتِ (#) وسطورَ الترخيص والفراغَ وBOM."""
    out=[]
    try: raw=Path(path).read_text(encoding="utf-8").splitlines()
    except Exception: return out
    for line in raw:
        s=" ".join(line.strip().lstrip("﻿").split())
        if not s or s.startswith("#"): continue
        out.append(s)
    return out

def load_quran_index(path):
    """فهرسٌ موحَّدٌ للاسترداد من نسختين إن توفّرتا: الرسمُ المشكّل (خنجريّة) للإخراج،
    والرسمُ المجرّد (إملائيّ) لتغطية الكتابة العاديّة. المفتاحُ = التطبيع، فيطابق
    اللصقُ العثمانيُّ والإملائيُّ معًا. تُفصَل البسملةُ المدموجةُ في أوّل كلّ سورة."""
    index={}
    def add(k,o):
        if k and k not in index: index[k]=o
    def add_verse(orig):
        k=_norm(orig); add(k,orig)
        if k.startswith(BISM_NORM+" "):                 # افصل البسملةَ المدموجة
            add(k[len(BISM_NORM)+1:]," ".join(orig.split()[4:]))
    prim=_read_edition(path)                             # الأولويّة للنسخة المشكّلة
    for o in prim: add_verse(o)
    # نسخةٌ مجرّدةٌ مرافقةٌ (إملائيّة) إن وُجدت — تُضيف مفاتيحَ لا تبدّل الموجود
    import os
    plain=os.path.join(os.path.dirname(path),"quran-simple-plain.txt")
    if os.path.abspath(plain)!=os.path.abspath(path):
        for o in _read_edition(plain): add_verse(o)
    # بنية محاذاةٍ للبحث عن المقاطع (من النسخة المشكّلة)
    valigned=[]
    for line in prim:
        dc=_declean(line)
        if not dc: continue
        nw=_norm(dc).split(); dw=dc.split()
        if len(nw)==len(dw) and nw: valigned.append((nw,dw))
    return index, " ".join(index.keys()), valigned

class ReverenceAwareUnified:
    def __init__(self, ckpt, quran_path, device, min_len=12):
        self.device=device; self.min_len=min_len
        print("📥 تحميل V3-unified (نموذج واحد للمجالين)...")
        self.model=load_model(ckpt, device)
        print("📖 بناء فهرس القرآن...")
        self.index,self.norm_full,self.valigned=load_quran_index(quran_path)
        self.keys_by_len=sorted(self.index.keys(), key=len, reverse=True)
        print(f"   {len(self.index):,} آية في الفهرس\n")

    def _frag_lookup(self, key, max_words=6):
        """استرداد مقطع قصير بأوّل مطابقة — بشرط اتّفاق تشكيله في كلّ مواضعه (يقين)."""
        fnw=key.split(); m=len(fnw)
        if m==0 or m>max_words: return None
        forms=set()
        for nw,dw in self.valigned:
            for p in range(len(nw)-m+1):
                if nw[p]==fnw[0] and nw[p:p+m]==fnw:
                    forms.add(" ".join(dw[p:p+m]))
                    if len(forms)>1: return None      # صيغتان مختلفتان → غير آمن → للنموذج
        return next(iter(forms)) if len(forms)==1 else None

    def process(self, text):
        key=_norm(text)
        if key in self.index:
            return {"route":"استرداد (آية تامّة)","reason":"تطابق تامّ (خطأ صفر)","output":self.index[key]}
        for vk in self.keys_by_len:
            if len(vk)<8: break
            if vk in key:
                return {"route":"استرداد (آية مضمّنة)","reason":"آية داخل سياق","output":self.index[vk]}
        if len(key)>=8 and len(key.split())>=2:
            k=len(key.split()); best=None
            for vk in self.keys_by_len:
                if vk.startswith(key+" "): best=vk
            if best is not None:
                return {"route":"استرداد (مقطع)","reason":"بداية آية","output":" ".join(self.index[best].split()[:k])}
        if len(key)>=self.min_len:
            for vk in reversed(self.keys_by_len):
                if key in vk:
                    return {"route":"استرداد (مقطع)","reason":"مقطع وسط آية","output":self.index[vk]}
        # المستوى 3ج: مقطع قصير مُتّفق التشكيل في كلّ القرآن → استرداد أوّل مطابقة (يقينيّ)
        if key in self.norm_full:
            ff=self._frag_lookup(key)
            if ff is not None:
                return {"route":"استرداد (مقطع مُتّفق)","reason":"مقطع صيغته واحدة في القرآن","output":ff}
        if len(key)>=self.min_len and key in self.norm_full:
            return {"route":"V3-unified (قرآنيّ)","reason":"محتوى قرآنيّ عابر","output":diacritize(text,self.model,self.device)}
        return {"route":"V3-unified (عامّ)","reason":"نصّ عامّ","output":diacritize(text,self.model,self.device)}

def main():
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ {device}\n")
    for p in (UNIFIED_CKPT, QURAN_PATH):
        if not Path(p).exists(): print(f"❌ مفقود: {p}"); sys.exit(1)
    sysm=ReverenceAwareUnified(UNIFIED_CKPT, QURAN_PATH, device)
    tests=["الحمد لله رب العالمين","انا اعطيناك الكوثر","قل هو الله احد",
           "ذهب الطالب الى المدرسة صباحا","قال العلماء ان التشكيل مهم"]
    print("="*72); print("Reverence-Aware Unified (نموذج واحد + استرداد)"); print("="*72)
    for t in tests:
        r=sysm.process(t)
        print(f"\n▌ {t}\n  التوجيه: {r['route']}\n  المخرج : {r['output']}")

if __name__=="__main__":
    main()
