# -*- coding: utf-8 -*-
"""
bert_graft_infer.py — استدلالٌ بنموذج BERT-graft (أقصى دقّة) لتشكيلٍ + استخراج الإعراب.
يُستعمل في التطبيق ونظام تعليم النطق. يحمّل outputs_bert_graft/model.pt.
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))          # scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))   # جذر المشروع
import torch
from transformers import AutoTokenizer
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           merge_letters_and_diacritics, strip_diacritics, PAD_ID)
from train_bert_graft import Graft, spans, MODEL_ID, INIT

NOM={3,7,11};ACC={1,5,9};JAR={2,6,10}
def case_label(c):
    if c in NOM: return "مرفوع"
    if c in ACC: return "منصوب"
    if c in JAR: return "مجرور"
    return "ساكن/مبنيّ"

class GraftInfer:
    def __init__(self, model_pt=None,
                 init=INIT, model_id=MODEL_ID, device=None):
        # اختر تلقائيًّا أفضل نقطةٍ متاحة
        if model_pt is None:
            for cand in ("outputs_bert_graft/best_model.pt","outputs_bert_graft/model.pt","outputs_bert_graft/latest.pt"):
                if Path(cand).exists(): model_pt=cand; break
            model_pt=model_pt or "outputs_bert_graft/model.pt"
        print(f"📥 نموذج: {model_pt}")
        self.dev=device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tok=AutoTokenizer.from_pretrained(model_id)
        self.model=Graft(model_id, init, self.dev).to(self.dev)
        sd=torch.load(model_pt, map_location=self.dev, weights_only=False)
        self.model.load_state_dict(sd["model_state"]); self.model.eval()
        import os as _os
        self.use_fp16 = _os.environ.get("GRAFT_FP16")=="1" and self.dev.type=="cuda"
        if self.use_fp16: print("⚡ fp16 (autocast)")

    @torch.no_grad()
    def _run(self, text):
        L,_=split_letters_and_diacritics(strip_diacritics(text))
        if not L: return L, []
        sp=spans(L); words=["".join(L[a:b]) for a,b in sp]
        woc=[-1]*len(L)
        for wi,(a,b) in enumerate(sp):
            for i in range(a,b): woc[i]=wi
        ci=torch.tensor([encode_chars(L)],device=self.dev)
        wocb=torch.tensor([woc],device=self.dev)
        attn=torch.ones_like(ci,dtype=torch.bool)
        enc=self.tok([words],is_split_into_words=True,padding=True,truncation=True,
                     max_length=384,return_tensors="pt").to(self.dev)
        with self._ac():
            pred=self.model(ci,wocb,attn,enc,[len(words)],self.dev).argmax(-1)[0].tolist()
        return L, pred

    # النموذجُ دُرّب على مقاطعَ ≤250 حرفًا؛ نقسّم الأطولَ عند الكلمات لتفادي تجاوز
    # الحدّ الأقصى لموضع المُشفّر (كان يسبّب خطأً في الفقرات الطويلة).
    MAXLEN=180
    def _chunks(self, text, maxlen=None):
        maxlen=maxlen or self.MAXLEN
        words=text.split(" "); chunks=[]; cur=[]; n=0
        for w in words:
            wl=len(strip_diacritics(w))+1
            if cur and n+wl>maxlen: chunks.append(" ".join(cur)); cur=[]; n=0
            cur.append(w); n+=wl
        if cur: chunks.append(" ".join(cur))
        return chunks or [text]

    def _apply_chunked(self, text, fn):
        parts=self._chunks(text)
        return fn(text) if len(parts)<=1 else " ".join(fn(p) for p in parts)

    def _diac_one(self, text):
        L,pred=self._run(text)
        if not L: return text
        return merge_letters_and_diacritics(L,[int(p) for p in pred])

    def diacritize(self, text):
        return self._apply_chunked(text, self._diac_one)

    # فئاتُ vocab_v2: 0∅ 1فتحة 2كسرة 3ضمّة 4سكون 5ً 6ٍ 7ٌ 8ّ 9ّ+فتحة 10ّ+كسرة 11ّ+ضمّة
    _SHADDA_ADD={1:9,5:9, 2:10,6:10, 3:11,7:11}
    def _combine(self, user_c, pred_c):
        """ادمج تشكيلَ المستخدم (إن وُجد) مع تنبّؤ النموذج: احترم الموجودَ، أكمِل الناقص."""
        if user_c==0: return pred_c                 # لا تشكيلَ من المستخدم ← النموذج
        if user_c==8:                               # شدّةٌ فقط ← أكمِل الحركةَ من النموذج
            if pred_c in (9,10,11): return pred_c
            return self._SHADDA_ADD.get(pred_c, 8)
        return user_c                               # تشكيلٌ كاملٌ من المستخدم ← احترمه

    def _diac_partial_one(self, text):
        L,C=split_letters_and_diacritics(text)      # التشكيلُ الموجود (0 = لا شيء)
        Lp,pred=self._run(text)                     # تنبّؤٌ محاذٍ للحروف نفسها
        if not L: return text
        if len(Lp)!=len(L):                         # احتياطٌ نادر
            return merge_letters_and_diacritics(Lp,[int(p) for p in pred]) if Lp else text
        out=[self._combine(int(C[i]), int(pred[i])) for i in range(len(L))]
        return merge_letters_and_diacritics(L,out)

    def _ac(self):
        import contextlib
        return (torch.autocast(device_type="cuda", dtype=torch.float16)
                if getattr(self,"use_fp16",False) else contextlib.nullcontext())

    @torch.no_grad()
    def _run_batch(self, texts):
        """تجميعُ عدّةِ جُملٍ في تمريرةٍ واحدة — نفسُ مسارِ _run بالضبط، مبطَّنٌ بالحشو."""
        items=[]
        for text in texts:
            L,_=split_letters_and_diacritics(strip_diacritics(text))
            sp=spans(L); words=["".join(L[a:b]) for a,b in sp]
            woc=[-1]*len(L)
            for wi,(a,b) in enumerate(sp):
                for i in range(a,b): woc[i]=wi
            items.append((L, encode_chars(L), woc, words))
        act=[i for i,it in enumerate(items) if it[0]]
        res=[None]*len(items)
        if not act: return [(it[0],[]) for it in items]
        Tc=max(len(items[i][1]) for i in act); B=len(act)
        ci=torch.full((B,Tc),PAD_ID,dtype=torch.long)
        woc=torch.full((B,Tc),-1,dtype=torch.long)
        attn=torch.zeros((B,Tc),dtype=torch.bool)
        word_lists=[]; nwords=[]
        for r,i in enumerate(act):
            L,c,w,words=items[i]; n=len(c)
            ci[r,:n]=torch.tensor(c); woc[r,:n]=torch.tensor(w); attn[r,:n]=True
            word_lists.append(words); nwords.append(len(words))
        ci=ci.to(self.dev); woc=woc.to(self.dev); attn=attn.to(self.dev)
        enc=self.tok(word_lists,is_split_into_words=True,padding=True,truncation=True,
                     max_length=384,return_tensors="pt").to(self.dev)
        with self._ac():
            preds=self.model(ci,woc,attn,enc,nwords,self.dev).argmax(-1)
        for r,i in enumerate(act):
            L,c,w,words=items[i]; n=len(c)
            res[i]=(L,[int(preds[r,k]) for k in range(n)])
        for i,it in enumerate(items):
            if res[i] is None: res[i]=(it[0],[])
        return res

    _BATCH_CAP = 480     # حدُّ أمانٍ لترميزِ الموضع (≤512)؛ الأطولُ يمرُّ بالمسارِ المقطَّع
    def diacritize_batch(self, texts):
        """تشكيلُ قائمةِ نصوصٍ: القصيرةُ تُجمَّعُ (سريع)، والطويلةُ تمرُّ بالمسارِ المقطَّعِ الآمن."""
        out=[None]*len(texts)
        short=[i for i,t in enumerate(texts) if len(strip_diacritics(t))<=self._BATCH_CAP]
        longi=[i for i in range(len(texts)) if i not in set(short)]
        if short:
            res=self._run_batch([texts[i] for i in short])
            for j,i in enumerate(short):
                L,pred=res[j]
                out[i]=merge_letters_and_diacritics(L,[int(p) for p in pred]) if L else texts[i]
        for i in longi:
            out[i]=self._apply_chunked(texts[i], self._diac_one)   # تقطيعٌ آمنٌ للطويل
        return out

    @torch.no_grad()
    def confidence(self, text):
        """يُرجِع (words, word_conf): أدنى ثقةِ softmax بين حروفِ كلِّ كلمة (0..1)."""
        L,_=split_letters_and_diacritics(strip_diacritics(text))
        if not L: return [], []
        sp=spans(L); words=["".join(L[a:b]) for a,b in sp]
        woc=[-1]*len(L)
        for wi,(a,b) in enumerate(sp):
            for i in range(a,b): woc[i]=wi
        ci=torch.tensor([encode_chars(L)],device=self.dev)
        wocb=torch.tensor([woc],device=self.dev)
        attn=torch.ones_like(ci,dtype=torch.bool)
        enc=self.tok([words],is_split_into_words=True,padding=True,truncation=True,
                     max_length=384,return_tensors="pt").to(self.dev)
        with self._ac():
            logits=self.model(ci,wocb,attn,enc,[len(words)],self.dev)[0]
        conf=torch.softmax(logits.float(),-1).max(-1).values.tolist()
        pred=logits.argmax(-1).tolist()
        wc=[(min(conf[a:b]) if b>a else 1.0) for a,b in sp]
        dw=[merge_letters_and_diacritics(L[a:b],[int(pred[i]) for i in range(a,b)]) for a,b in sp]
        return dw, wc

    def diacritize_partial(self, text):
        """يحترم التشكيلَ الموجودَ في الإدخال ويُكمّل الحروفَ غيرَ المشكّلة فقط."""
        return self._apply_chunked(text, self._diac_partial_one)

    def iraab(self, text):
        """أرجع لكلّ كلمة: (الكلمة المشكّلة, حركة الآخِر, وسم الإعراب)."""
        L,pred=self._run(text)
        if not L: return []
        out=[]
        for a,b in spans(L):
            w=merge_letters_and_diacritics(L[a:b],[int(pred[i]) for i in range(a,b)])
            fin=int(pred[b-1])
            out.append((w, fin, case_label(fin)))
        return out
