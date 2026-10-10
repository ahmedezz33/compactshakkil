# -*- coding: utf-8 -*-
"""
train_bert_graft.py — النسخة 2: تطعيم سياق CAMeLBERT على النموذج القويّ v3-hard.

بدل تدريب رأسٍ حرفيٍّ ضعيفٍ من الصفر (النسخة 1 التي أضرّت بالبنية)، نبدأ من
CompactShakkilBase المُتقَن (v3-hard، بنية 1.72%) ونضيف متّجه BERT للكلمة كإشارةٍ
سياقيّة إلى تضمين الحرف. فتبقى البنية ممتازةً، ويُحسّن سياق BERT حركةَ الآخِر.

التطعيم: proj(BERT_word) يُضاف إلى تضمين الحرف قبل مُشفّر النموذج الأصليّ.
proj مُهيّأ صغيرًا؛ نصقل الكلّ (BERT lr منخفض، النموذج والوصلة أعلى).

تجربة سريعة: python scripts/train_bert_graft.py smoke
كامل:        python scripts/train_bert_graft.py full
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
from models.transformer import CompactShakkilBase

MODEL_ID="CAMeL-Lab/bert-base-arabic-camelbert-ca"
GEN="data/processed_clean"
INIT="outputs_v3_hard/best_model.pt"      # النموذج القويّ الذي نطعّمه
NOM={3,7,11};ACC={1,5,9};JAR={2,6,10}

def spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp

def load(path,n,seed,lo=3,hi=250):
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
        tgt=[(-100 if L[i]==" " else int(C[i])) for i in range(len(L))]
        out.append((encode_chars(L),tgt,woc,words))
    random.Random(seed).shuffle(out)
    return out[:n] if n else out

class Graft(nn.Module):
    def __init__(self, model_id, init_ckpt, dev):
        super().__init__()
        # النموذج الأصليّ (بأبعاد v3-hard)
        ck=torch.load(init_ckpt, map_location=dev, weights_only=False); m=ck["config"]["model"]
        self.d=m["d_model"]
        self.base=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_DIACRITIC_CLASSES,
            d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
            dim_feedforward=m["dim_feedforward"],dropout=m["dropout"],max_position=m["max_position"],pad_id=PAD_ID)
        self.base.load_state_dict(ck["model_state"]); print(f"📥 طُعِّم على {init_ckpt}")
        self.bert=AutoModel.from_pretrained(model_id, use_safetensors=True)
        self.proj=nn.Linear(self.bert.config.hidden_size, self.d)
        nn.init.normal_(self.proj.weight, std=0.02); nn.init.zeros_(self.proj.bias)

    def word_vecs(self, enc, nwords_list, device):
        H=self.bert(**enc).last_hidden_state
        outs=[]
        for b,nw in enumerate(nwords_list):
            wids=enc.word_ids(b); Hb=H[b]
            V=torch.zeros(nw,H.size(-1),device=device); cnt=torch.zeros(nw,device=device)
            for t,wid in enumerate(wids):
                if wid is not None and wid<nw: V[wid]+=Hb[t]; cnt[wid]+=1
            outs.append(V/cnt.clamp(min=1).unsqueeze(1))
        return outs

    def forward(self, char_ids, woc, attn, enc, nwords_list, device):
        Vs=self.word_vecs(enc,nwords_list,device)
        B,Tc=char_ids.shape
        feats=[]
        for b in range(B):
            cw=woc[b]; idx=cw.clamp(min=0); f=Vs[b][idx]
            f=f.masked_fill((cw<0).unsqueeze(1),0.0); feats.append(f)
        wf=torch.stack(feats,0)                                  # [B,Tc,h]
        # مسار النموذج الأصليّ + إشارة BERT مطعّمة
        x=self.base.embedding(char_ids)*math.sqrt(self.d) + self.proj(wf)
        x=self.base.pos_encoding(x); x=self.base.input_dropout(x)
        x=self.base.encoder(x, src_key_padding_mask=~attn)
        return self.base.classifier(x)

def collate(batch, tok, device):
    Tc=max(len(c) for c,_,_,_ in batch); B=len(batch)
    ci=torch.full((B,Tc),PAD_ID,dtype=torch.long); tg=torch.full((B,Tc),-100,dtype=torch.long)
    woc=torch.full((B,Tc),-1,dtype=torch.long); attn=torch.zeros((B,Tc),dtype=torch.bool)
    word_lists=[]; nwords=[]
    for i,(c,t,w,words) in enumerate(batch):
        n=len(c); ci[i,:n]=torch.tensor(c); tg[i,:n]=torch.tensor(t); woc[i,:n]=torch.tensor(w); attn[i,:n]=True
        word_lists.append(words); nwords.append(len(words))
    enc=tok(word_lists,is_split_into_words=True,padding=True,truncation=True,max_length=384,return_tensors="pt").to(device)
    return ci.to(device),woc.to(device),attn.to(device),enc,nwords,tg.to(device)

def fam(c): return 'n' if c in NOM else 'a' if c in ACC else 'g' if c in JAR else 'o'

@torch.no_grad()
def evaluate(model,data,tok,dev,bs=16):
    model.eval(); tot=err=ft=fe=it=ie=0
    for i in range(0,len(data),bs):
        batch=data[i:i+bs]; ci,woc,attn,enc,nwords,tg=collate(batch,tok,dev)
        pred=model(ci,woc,attn,enc,nwords,dev).argmax(-1)
        for b,(c,t,w,words) in enumerate(batch):
            n=len(c); fin=set()
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
    mode=sys.argv[1] if len(sys.argv)>1 else "full"; smoke=(mode=="smoke")
    init=sys.argv[2] if len(sys.argv)>2 else INIT     # أساسٌ بديل (مثل outputs_v4_big/best_model.pt)
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"الوضع={mode} | {dev} | {MODEL_ID} | أساس={init}")
    tok=AutoTokenizer.from_pretrained(MODEL_ID)
    model=Graft(MODEL_ID, init, dev).to(dev)
    gen=GEN
    if smoke:   n_train,epochs = 300, 1
    elif mode=="max":                                # أقصى دقّة: كلُّ البيانات النظيفة الموسَّعة
        gen="data/processed_max"; n_train,epochs = None, 2
    else:       n_train,epochs = 300000, 2
    # التقييمُ دائمًا على مجموعةٍ خاليةٍ من التسرُّب
    testp="data/processed_clean/test_noleak.txt"
    tr=load(f"{gen}/train.txt",n_train,seed=1); te=load(testp,200 if smoke else 4000,seed=2)
    print(f"مصدرُ التدريب: {gen}/train.txt | التقييم: {testp}")
    print(f"تدريب={len(tr):,} اختبار={len(te):,}")
    bert_p=list(model.bert.parameters())
    other_p=[p for nm,p in model.named_parameters() if not nm.startswith("bert.")]
    opt=torch.optim.AdamW([{"params":bert_p,"lr":1e-5},{"params":other_p,"lr":1e-4}],weight_decay=0.01)
    crit=nn.CrossEntropyLoss(ignore_index=-100)
    scaler=torch.amp.GradScaler(enabled=(dev.type=="cuda"))
    BS=8 if smoke else 12
    total=max(1,(len(tr)//BS)*epochs); warm=max(10,total//20)
    def lr_at(s):
        if s<warm: return s/warm
        p=(s-warm)/max(1,total-warm); return max(0.02,0.5*(1+math.cos(math.pi*p)))
    sch=torch.optim.lr_scheduler.LambdaLR(opt, lr_at)
    outdir=sys.argv[3] if len(sys.argv)>3 else "outputs_bert_graft"   # وجهةٌ بديلة تحمي نموذج 1.09٪
    out=Path(outdir); out.mkdir(exist_ok=True)
    def save(name): torch.save({"model_state":model.state_dict(),"model_id":MODEL_ID},out/name)
    print("— الأساس قبل التطعيم —"); best=evaluate(model,te,tok,dev)
    EVAL_EVERY=0 if smoke else 20000        # تقييمٌ وحفظٌ دوريٌّ (يأمن الإيقاف في الحقب الطويلة)
    step=0
    for ep in range(epochs):
        model.train(); random.shuffle(tr)
        for i in range(0,len(tr),BS):
            batch=tr[i:i+BS]; ci,woc,attn,enc,nwords,tg=collate(batch,tok,dev)
            with torch.amp.autocast(device_type=dev.type,enabled=(dev.type=="cuda")):
                logits=model(ci,woc,attn,enc,nwords,dev)
                loss=crit(logits.reshape(-1,NUM_DIACRITIC_CLASSES),tg.reshape(-1))
            opt.zero_grad(); scaler.scale(loss).backward()
            scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(),1.0)
            scaler.step(opt); scaler.update(); sch.step(); step+=1
            if step%100==0: print(f"  ep{ep} step{step} loss={loss.item():.3f} lr={sch.get_last_lr()[1]:.2e}")
            if EVAL_EVERY and step%EVAL_EVERY==0:
                print(f"— تقييمٌ دوريّ (خطوة {step}) —"); der=evaluate(model,te,tok,dev); save("latest.pt")
                if der<best: best=der; save("best_model.pt"); print(f"   ✅ أفضل DER={der:.2f}% — حُفظ best_model.pt")
                model.train()
            if smoke and step>=20: break
        print(f"— تقييم بعد الحقبة {ep} —"); der=evaluate(model,te,tok,dev)
        save("latest.pt")
        if der<best: best=der; save("best_model.pt"); print(f"   ✅ أفضل DER={der:.2f}% — حُفظ best_model.pt")
    print(f"✅ انتهى. أفضل DER={best:.2f}%  (محفوظ: outputs_bert_graft/best_model.pt)")
    print("الأساس المُدمَج: DER 2.05 | بنية 1.72 | آخِر 3.01")

if __name__=="__main__":
    main()
