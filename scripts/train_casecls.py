# -*- coding: utf-8 -*-
"""
train_casecls.py — مُصنِّف عائلة الحالة الإعرابيّة (متخصّص).

المُدخَل: أحرف بلا تشكيل. الهدف: عائلة الحالة لكلّ حرف (من ملفّات الأوراكل):
    2=غير ذلك ، 3=مرفوع ، 4=منصوب ، 5=مجرور  (المسافة/الحشو → تُتجاهَل).
يستعمل CompactShakkilBase برأس 6 فئات. الهدف: تجاوز حاجز الأساس (97.45% عائلة).

الاستخدام: python scripts/train_casecls.py --config configs/config_casecls.yaml
"""
from __future__ import annotations
import argparse, sys, math, random
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import yaml, numpy as np, torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import split_letters_and_diacritics, encode_chars, VOCAB_SIZE, PAD_ID
from models.transformer import CompactShakkilBase

NUM_CASE=6           # 0..5 (المستعمَل فعليًّا 2..5)
SPACE_ID=1

def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)

def read_pair(txt,pos,ml,cap=0):
    out=[]
    with open(txt,encoding="utf-8") as f, open(pos,encoding="utf-8") as g:
        for line,pl in zip(f,g):
            line=line.strip(); pl=pl.strip()
            if not line: continue
            L,_=split_letters_and_diacritics(line)
            if len(L)<3 or len(L)>ml: continue
            fam=[int(x) for x in pl.split()]
            if len(fam)!=len(L): continue
            # الهدف: المسافة → -100 (تُتجاهَل)
            tgt=[-100 if f==SPACE_ID else f for f in fam]
            out.append((encode_chars(L),tgt))
            if cap and len(out)>=cap: return out
    return out

class DS(Dataset):
    def __init__(self,txt,pos,ml,cap):
        print(f"📂 {txt}"); self.s=read_pair(txt,pos,ml,cap); print(f"   {len(self.s):,}")
    def __len__(self): return len(self.s)
    def __getitem__(self,i):
        a,t=self.s[i]
        return {"input_ids":torch.tensor(a),"target_ids":torch.tensor(t)}

def collate(b):
    mx=max(len(x["input_ids"]) for x in b); B=len(b)
    ii=torch.full((B,mx),PAD_ID,dtype=torch.long); tg=torch.full((B,mx),-100,dtype=torch.long)
    mk=torch.zeros((B,mx),dtype=torch.bool)
    for i,x in enumerate(b):
        L=len(x["input_ids"]); ii[i,:L]=x["input_ids"]; tg[i,:L]=x["target_ids"]; mk[i,:L]=True
    return {"input_ids":ii,"target_ids":tg,"attention_mask":mk}

def cosine(o,w,t):
    def f(s):
        if s<w: return s/max(1,w)
        p=(s-w)/max(1,t-w); return max(0.0,0.5*(1+math.cos(math.pi*p)))
    return LambdaLR(o,f)

@torch.no_grad()
def evaluate(model,loader,device):
    model.eval(); c=v=0
    for b in loader:
        ii=b["input_ids"].to(device);tg=b["target_ids"].to(device);mk=b["attention_mask"].to(device)
        lg=model(ii,mk); pr=lg.argmax(-1); m=tg!=-100
        c+=((pr==tg)&m).sum().item(); v+=m.sum().item()
    return c/max(1,v)

def train(cfg):
    set_seed(cfg["seed"])
    device=torch.device("cuda" if (cfg["device"]["use_cuda"] and torch.cuda.is_available()) else "cpu")
    ml=cfg["data"]["max_seq_length"]; d=cfg["data"]
    tr=DS(d["gen_dir"]+"/train.txt", d["pos_dir"]+"/train.pos", ml, d["gen_cap"])
    va=DS(d["gen_dir"]+"/val.txt", d["pos_dir"]+"/val.pos", ml, d["val_cap"])
    trl=DataLoader(tr,batch_size=cfg["training"]["batch_size"],shuffle=True,collate_fn=collate,
                   num_workers=cfg["device"]["num_workers"],pin_memory=cfg["device"]["pin_memory"])
    val=DataLoader(va,batch_size=cfg["training"]["batch_size"],shuffle=False,collate_fn=collate)
    m=cfg["model"]
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_CASE,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=m["dropout"],max_position=m["max_position"],pad_id=PAD_ID).to(device)
    print(f"   معاملات: {model.count_parameters():,}  | الحاجز=97.45% عائلة")
    crit=nn.CrossEntropyLoss(ignore_index=-100)
    opt=AdamW(model.parameters(),lr=cfg["training"]["learning_rate"],weight_decay=cfg["training"]["weight_decay"])
    maxs=cfg["training"]["max_steps"]; accum=cfg["training"]["gradient_accumulation"]
    sch=cosine(opt,cfg["training"]["warmup_steps"],maxs)
    scaler=torch.amp.GradScaler(enabled=(cfg["device"]["mixed_precision"]=="fp16"))
    out=Path(cfg["logging"]["output_dir"]); out.mkdir(parents=True,exist_ok=True)
    ei=cfg["logging"]["eval_interval"]
    def save(n,st,acc): torch.save({"model_state":model.state_dict(),"config":cfg,"step":st,"acc":acc,"arch":"casecls","num_case":NUM_CASE},out/n)
    print(f"🚀 تدريب مُصنِّف الحالة — سقف {maxs}\n"); g=0;best=0.0;done=False;model.train()
    while not done:
        for step,b in enumerate(tqdm(trl,desc="casecls")):
            ii=b["input_ids"].to(device,non_blocking=True);tg=b["target_ids"].to(device,non_blocking=True);mk=b["attention_mask"].to(device,non_blocking=True)
            with torch.amp.autocast(device_type=device.type,enabled=(device.type=="cuda")):
                lg=model(ii,mk); loss=crit(lg.reshape(-1,NUM_CASE),tg.reshape(-1))/accum
            scaler.scale(loss).backward()
            if (step+1)%accum==0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["training"]["max_grad_norm"])
                scaler.step(opt); scaler.update(); sch.step(); opt.zero_grad(set_to_none=True); g+=1
                if g%ei==0:
                    acc=evaluate(model,val,device); print(f"\n   step {g}: val عائلة(كلّ الأحرف)={acc:.4f}")
                    save("latest.pt",g,acc)
                    if acc>best: best=acc; save("best_model.pt",g,acc); print(f"   ✅ أفضل: {acc:.4f}")
                    model.train()
                if g>=maxs: done=True; break
    save("latest.pt",g,best)
    print(f"\n✅ انتهى. أفضل val عائلة={best:.4f}")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/config_casecls.yaml")
    with open(ap.parse_args().config,encoding="utf-8") as _f: _cfg=yaml.safe_load(_f)
    train(_cfg)
