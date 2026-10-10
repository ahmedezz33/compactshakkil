# -*- coding: utf-8 -*-
"""
bert_case_probe.py — الاختبار الحاسم لمسار «النموذج اللغويّ الضخم».

يصقل نموذجًا عربيًّا مُدرَّبًا مسبقًا (CAMeLBERT الكلاسيكيّ افتراضيًّا) للتنبّؤ
بعائلة الحالة الإعرابيّة عند آخِر الكلمة {مرفوع/منصوب/مجرور/غير-ذلك}، ويقيسه
مقابل حاجز النموذج المُدمَج (97.45%). إن تجاوزه بوضوح، فمسار الـ LM يكسر السقف.

المتطلّبات: torch (مثبّت) + transformers  →  pip install transformers
أوّل تشغيل يُنزّل أوزان النموذج (~500MB) — يتطلّب إنترنت.
الاستخدام: python scripts/bert_case_probe.py [model_id] [train.txt] [test.txt] [n_train] [epochs]
"""
import sys, random
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch, torch.nn as nn
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, AutoModel
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import split_letters_and_diacritics

NOM={3,7,11}; ACC={1,5,9}; GEN={2,6,10}
def fam_id(c):
    if c in NOM: return 1
    if c in ACC: return 2
    if c in GEN: return 3
    return 0                     # غير ذلك (∅/سكون)
NUM=4; BAR=97.45

def load_words(path, n, seed=42, lo=3, hi=200):
    """أرجع [(words, fams)] : كلمات بلا تشكيل + عائلة الحالة لآخِر كلّ كلمة."""
    out=[]
    for line in open(path,encoding="utf-8"):
        s=line.strip()
        if not s: continue
        L,C=split_letters_and_diacritics(s)
        if len(L)<lo or len(L)>hi: continue
        # قسّم إلى كلمات + عائلة آخِر كلّ كلمة
        words=[]; fams=[]; st=None
        for i,ch in enumerate(L+[" "]):
            if ch==" ":
                if st is not None:
                    words.append("".join(L[st:i])); fams.append(fam_id(int(C[i-1]))); st=None
            else:
                if st is None: st=i
        if words: out.append((words,fams))
    random.Random(seed).shuffle(out)
    return out[:n] if n else out

class Probe(nn.Module):
    def __init__(self, model_id):
        super().__init__()
        self.bert=AutoModel.from_pretrained(model_id, use_safetensors=True)
        h=self.bert.config.hidden_size
        self.head=nn.Linear(h, NUM)
    def forward(self, enc, last_idx_batch):
        H=self.bert(**enc).last_hidden_state           # [B,T,h]
        feats=[];
        for i,idxs in enumerate(last_idx_batch):
            feats.append(H[i, idxs])                    # [W_i, h]
        return feats                                    # قائمة تنسورات

def build_batch(batch, tok, device):
    word_lists=[w for w,_ in batch]
    enc=tok(word_lists, is_split_into_words=True, padding=True, truncation=True,
            max_length=256, return_tensors="pt")
    last_idx=[]; targets=[]
    for i,(words,fams) in enumerate(batch):
        wids=enc.word_ids(i)
        # آخر توكِن لكلّ كلمة (ضمن max_length)
        last={}
        for pos,wid in enumerate(wids):
            if wid is not None: last[wid]=pos
        idxs=[]; tg=[]
        for w in range(len(words)):
            if w in last: idxs.append(last[w]); tg.append(fams[w])
        last_idx.append(torch.tensor(idxs,dtype=torch.long))
        targets.append(torch.tensor(tg,dtype=torch.long,device=device))
    enc={k:v.to(device) for k,v in enc.items()}
    return enc, last_idx, targets

def main():
    model_id=sys.argv[1] if len(sys.argv)>1 else "CAMeL-Lab/bert-base-arabic-camelbert-ca"
    trainp =sys.argv[2] if len(sys.argv)>2 else "data/processed_clean/train.txt"
    testp  =sys.argv[3] if len(sys.argv)>3 else "data/processed_clean/test.txt"
    n_train=int(sys.argv[4]) if len(sys.argv)>4 else 40000
    epochs =int(sys.argv[5]) if len(sys.argv)>5 else 2
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"النموذج: {model_id}"); tok=AutoTokenizer.from_pretrained(model_id)
    model=Probe(model_id).to(dev)
    tr=load_words(trainp,n_train,seed=1); te=load_words(testp,4000,seed=2)
    print(f"تدريب={len(tr):,} جملة  اختبار={len(te):,}")
    opt=torch.optim.AdamW(model.parameters(),lr=2e-5,weight_decay=0.01)
    crit=nn.CrossEntropyLoss()
    def loader(data,bs,shuf):
        idx=list(range(len(data)))
        if shuf: random.shuffle(idx)
        for i in range(0,len(idx),bs): yield [data[j] for j in idx[i:i+bs]]
    BS=16; step=0
    for ep in range(epochs):
        model.train()
        for batch in loader(tr,BS,True):
            enc,last_idx,targets=build_batch(batch,tok,dev)
            feats=model(enc,last_idx)
            allf=torch.cat(feats,0); allt=torch.cat(targets,0)
            logit=model.head(allf); loss=crit(logit,allt)
            opt.zero_grad(); loss.backward(); opt.step(); step+=1
            if step%200==0: print(f"  ep{ep} step{step} loss={loss.item():.3f}")
    # تقييم
    model.eval(); cor=tot=0
    with torch.no_grad():
        for batch in loader(te,BS,False):
            enc,last_idx,targets=build_batch(batch,tok,dev)
            feats=model(enc,last_idx)
            allf=torch.cat(feats,0); allt=torch.cat(targets,0)
            pred=model.head(allf).argmax(-1)
            cor+=(pred==allt).sum().item(); tot+=allt.numel()
    acc=100*cor/max(1,tot)
    print("="*60)
    print(f"دقّة عائلة الحالة (BERT، نهاية الكلمة) = {acc:.2f}%  ({tot:,} كلمة)")
    print(f"حاجز النموذج المُدمَج                  = {BAR}%")
    d=acc-BAR
    print(f"الفرق = {d:+.2f} نقطة  →  " + ("يتجاوز ✅ مسار الـLM يكسر السقف — نبني المُشكِّل الكامل" if d>0.5 else ("متعادل ⚖️ — لا جدوى تُذكر" if abs(d)<=0.5 else "دون الحاجز ❌ — حتّى الـLM لا يكسر السقف")))
    print("="*60)

if __name__=="__main__":
    main()
