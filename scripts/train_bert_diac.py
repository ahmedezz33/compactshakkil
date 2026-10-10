# -*- coding: utf-8 -*-
"""
train_bert_diac.py — مُشكِّلٌ كاملٌ على CAMeLBERT (أقصى دقّة، الإعراب هدفٌ رئيس).

المعماريّة: CAMeLBERT يعطي تمثيلًا سياقيًّا لكلّ كلمة → يُحقَن في مجرى الحروف
(مع تضمين الحرف نفسه) → رأسٌ Transformer حرفيّ صغير → فئة حركةٍ لكلّ حرف.
يجمع فهمَ BERT السياقيّ (للإعراب) بدقّة الحرف (للبنية).

المتطلّبات: torch + transformers (safetensors).
تجربةٌ سريعة أوّلًا:   python scripts/train_bert_diac.py smoke
التدريب الكامل:        python scripts/train_bert_diac.py full
"""
import sys, random, math
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import torch, torch.nn as nn
from transformers import AutoTokenizer, AutoModel
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)

MODEL_ID = "CAMeL-Lab/bert-base-arabic-camelbert-ca"
GEN = "data/processed_clean"
D = 256            # بُعد الرأس الحرفيّ
SPACE_TGT = -100   # المسافة لا تُشرَف

# ---------- بيانات ----------
def spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp

def load(path, n, seed, lo=3, hi=250):
    """أرجع [(char_ids, targets, word_of_char, words)]."""
    out=[]
    for line in open(path,encoding="utf-8"):
        s=line.strip()
        if not s: continue
        L,C=split_letters_and_diacritics(s)
        if len(L)<lo or len(L)>hi: continue
        sp=spans(L)
        if not sp: continue
        words=["".join(L[a:b]) for a,b in sp]
        woc=[-1]*len(L)
        for wi,(a,b) in enumerate(sp):
            for i in range(a,b): woc[i]=wi
        tgt=[(SPACE_TGT if L[i]==" " else int(C[i])) for i in range(len(L))]
        out.append((encode_chars(L), tgt, woc, words))
    random.Random(seed).shuffle(out)
    return out[:n] if n else out

# ---------- النموذج ----------
class PositionalEncoding(nn.Module):
    def __init__(self, d, mx=512):
        super().__init__()
        pe=torch.zeros(mx,d); pos=torch.arange(0,mx).unsqueeze(1).float()
        div=torch.exp(torch.arange(0,d,2).float()*(-math.log(10000.0)/d))
        pe[:,0::2]=torch.sin(pos*div); pe[:,1::2]=torch.cos(pos*div)
        self.register_buffer("pe",pe.unsqueeze(0))
    def forward(self,x): return x+self.pe[:,:x.size(1)]

class BertDiacritizer(nn.Module):
    def __init__(self, model_id):
        super().__init__()
        self.bert=AutoModel.from_pretrained(model_id, use_safetensors=True)
        h=self.bert.config.hidden_size
        self.char_emb=nn.Embedding(VOCAB_SIZE, D, padding_idx=PAD_ID)
        self.proj=nn.Linear(h, D)
        self.pe=PositionalEncoding(D, mx=512)
        layer=nn.TransformerEncoderLayer(d_model=D, nhead=8, dim_feedforward=1024,
                                         dropout=0.1, activation="gelu", batch_first=True, norm_first=True)
        self.head=nn.TransformerEncoder(layer, num_layers=3)
        self.cls=nn.Sequential(nn.Linear(D,D), nn.GELU(), nn.Dropout(0.1), nn.Linear(D,NUM_DIACRITIC_CLASSES))

    def word_vecs(self, enc, nwords_list, device):
        H=self.bert(**enc).last_hidden_state           # [B,T,h]
        outs=[]
        for b,nw in enumerate(nwords_list):
            wids=enc.word_ids(b); Hb=H[b]
            V=torch.zeros(nw, H.size(-1), device=device); cnt=torch.zeros(nw, device=device)
            for t,wid in enumerate(wids):
                if wid is not None and wid<nw: V[wid]+=Hb[t]; cnt[wid]+=1
            outs.append(V/cnt.clamp(min=1).unsqueeze(1))
        return outs                                     # قائمة [nw,h]

    def forward(self, char_ids, woc, attn, enc, nwords_list, device):
        Vs=self.word_vecs(enc, nwords_list, device)     # قائمة [nw,h]
        B,Tc=char_ids.shape
        feats=[]
        for b in range(B):
            cw=woc[b]                                    # [Tc] بقيم -1 للمسافة/الحشو
            idx=cw.clamp(min=0)
            f=Vs[b][idx]                                 # [Tc,h]
            f=f.masked_fill((cw<0).unsqueeze(1), 0.0)
            feats.append(f)
        wordfeat=torch.stack(feats,0)                   # [B,Tc,h]
        x=self.char_emb(char_ids)*math.sqrt(D) + self.proj(wordfeat)
        x=self.pe(x)
        x=self.head(x, src_key_padding_mask=~attn)
        return self.cls(x)                              # [B,Tc,classes]

# ---------- تجميع الدفعة ----------
def collate(batch, tok, device):
    Tc=max(len(c) for c,_,_,_ in batch); B=len(batch)
    char_ids=torch.full((B,Tc),PAD_ID,dtype=torch.long)
    tgt=torch.full((B,Tc),-100,dtype=torch.long)
    woc=torch.full((B,Tc),-1,dtype=torch.long)
    attn=torch.zeros((B,Tc),dtype=torch.bool)
    word_lists=[]; nwords=[]
    for i,(c,t,w,words) in enumerate(batch):
        n=len(c); char_ids[i,:n]=torch.tensor(c); tgt[i,:n]=torch.tensor(t)
        woc[i,:n]=torch.tensor(w); attn[i,:n]=True
        word_lists.append(words); nwords.append(len(words))
    enc=tok(word_lists, is_split_into_words=True, padding=True, truncation=True,
            max_length=384, return_tensors="pt")
    enc=enc.to(device)
    return (char_ids.to(device), woc.to(device), attn.to(device),
            enc, nwords, tgt.to(device))

# ---------- تقييم ----------
def wspans(L):
    return spans(L)
NOM={3,7,11};ACC={1,5,9};JAR={2,6,10}
def fam(c): return 'n' if c in NOM else 'a' if c in ACC else 'g' if c in JAR else 'o'

@torch.no_grad()
def evaluate(model, data, tok, device, bs=16):
    model.eval(); tot=err=ft=fe=it=ie=0
    # نحتاج L الأصليّ لتحديد الأواخر — نعيد اشتقاقها من char_ids؟ الأسهل تمرير L.
    for i in range(0,len(data),bs):
        batch=data[i:i+bs]
        ci,woc,attn,enc,nwords,tgt=collate(batch,tok,device)
        logits=model(ci,woc,attn,enc,nwords,device); pred=logits.argmax(-1)
        for b,(c,t,w,words) in enumerate(batch):
            n=len(c)
            # مواضع الأواخر: آخر حرفٍ قبل تغيّر رقم الكلمة
            fin=set()
            for k in range(n):
                if w[k]!=-1 and (k+1>=n or w[k+1]!=w[k]): fin.add(k)
            for k in range(n):
                if t[k]==-100: continue
                tot+=1; isf=k in fin
                if isf: ft+=1
                else: it+=1
                if int(pred[b,k])!=t[k]:
                    err+=1
                    if isf: fe+=1
                    else: ie+=1
    print(f"  DER={100*err/tot:.2f}%  بنية={100*ie/it:.2f}%  حركة الآخِر={100*fe/ft:.2f}%")
    return 100*err/tot

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else "full"
    smoke = (mode=="smoke")
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"الوضع={mode} | جهاز={dev} | {MODEL_ID}")
    tok=AutoTokenizer.from_pretrained(MODEL_ID)
    model=BertDiacritizer(MODEL_ID).to(dev)
    n_train = 300 if smoke else 300000
    epochs  = 1 if smoke else 2
    tr=load(f"{GEN}/train.txt", n_train, seed=1)
    te=load(f"{GEN}/test.txt", 200 if smoke else 4000, seed=2)
    print(f"تدريب={len(tr):,} اختبار={len(te):,}")
    # معدّلات مختلفة: BERT منخفض، الرأس أعلى
    bert_params=list(model.bert.parameters())
    head_params=[p for n,p in model.named_parameters() if not n.startswith("bert.")]
    opt=torch.optim.AdamW([{"params":bert_params,"lr":2e-5},{"params":head_params,"lr":3e-4}], weight_decay=0.01)
    crit=nn.CrossEntropyLoss(ignore_index=-100)
    scaler=torch.amp.GradScaler(enabled=(dev.type=="cuda"))
    BS=8 if smoke else 12; step=0
    for ep in range(epochs):
        model.train(); random.shuffle(tr)
        for i in range(0,len(tr),BS):
            batch=tr[i:i+BS]
            ci,woc,attn,enc,nwords,tgt=collate(batch,tok,dev)
            with torch.amp.autocast(device_type=dev.type,enabled=(dev.type=="cuda")):
                logits=model(ci,woc,attn,enc,nwords,dev)
                loss=crit(logits.reshape(-1,NUM_DIACRITIC_CLASSES),tgt.reshape(-1))
            opt.zero_grad(); scaler.scale(loss).backward()
            scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(),1.0)
            scaler.step(opt); scaler.update(); step+=1
            if step%100==0: print(f"  ep{ep} step{step} loss={loss.item():.3f}")
            if smoke and step>=20: break
        print(f"— تقييم بعد الحقبة {ep} —"); evaluate(model, te, tok, dev)
    out=Path("outputs_bert_diac"); out.mkdir(exist_ok=True)
    torch.save({"model_state":model.state_dict(),"model_id":MODEL_ID}, out/"model.pt")
    print("✅ محفوظ في outputs_bert_diac/model.pt")
    print("الأساس المُدمَج: DER 2.05 | بنية 1.72 | آخِر 3.01")

if __name__=="__main__":
    main()
