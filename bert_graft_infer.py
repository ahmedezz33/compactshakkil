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
        pred=self.model(ci,wocb,attn,enc,[len(words)],self.dev).argmax(-1)[0].tolist()
        return L, pred

    def diacritize(self, text):
        L,pred=self._run(text)
        if not L: return text
        return merge_letters_and_diacritics(L,[int(p) for p in pred])

    # فئاتُ vocab_v2: 0∅ 1فتحة 2كسرة 3ضمّة 4سكون 5ً 6ٍ 7ٌ 8ّ 9ّ+فتحة 10ّ+كسرة 11ّ+ضمّة
    _SHADDA_ADD={1:9,5:9, 2:10,6:10, 3:11,7:11}
    def _combine(self, user_c, pred_c):
        """ادمج تشكيلَ المستخدم (إن وُجد) مع تنبّؤ النموذج: احترم الموجودَ، أكمِل الناقص."""
        if user_c==0: return pred_c                 # لا تشكيلَ من المستخدم ← النموذج
        if user_c==8:                               # شدّةٌ فقط ← أكمِل الحركةَ من النموذج
            if pred_c in (9,10,11): return pred_c
            return self._SHADDA_ADD.get(pred_c, 8)
        return user_c                               # تشكيلٌ كاملٌ من المستخدم ← احترمه

    def diacritize_partial(self, text):
        """يحترم التشكيلَ الموجودَ في الإدخال ويُكمّل الحروفَ غيرَ المشكّلة فقط."""
        L,C=split_letters_and_diacritics(text)      # التشكيلُ الموجود (0 = لا شيء)
        Lp,pred=self._run(text)                     # تنبّؤٌ محاذٍ للحروف نفسها
        if not L: return text
        if len(Lp)!=len(L):                         # احتياطٌ نادر
            return merge_letters_and_diacritics(Lp,[int(p) for p in pred]) if Lp else text
        out=[self._combine(int(C[i]), int(pred[i])) for i in range(len(L))]
        return merge_letters_and_diacritics(L,out)

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
