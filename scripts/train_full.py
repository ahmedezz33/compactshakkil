# -*- coding: utf-8 -*-
"""
train_full.py — تدريب CompactShakkilBase (أيّ حجم) من الصفر على كامل البيانات العامّة.
بلا ميزة، بلا قرآن، بلا نقطة انطلاق — لقياس أثر السعة على النشر.
الاستخدام: python scripts/train_full.py --config configs/config_big_full.yaml
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
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from models.transformer import CompactShakkilBase

def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)

def read_file(path, ml, cap=0):
    out=[]
    with open(path, encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            L,C=split_letters_and_diacritics(line)
            if len(L)<3 or len(L)>ml: continue
            out.append((encode_chars(L),C))
            if cap and len(out)>=cap: break
    return out

class DS(Dataset):
    def __init__(self, path, ml, cap):
        print(f"📂 {path} (حدّ={cap or 'بلا'})"); self.s=read_file(path,ml,cap); print(f"   {len(self.s):,}")
    def __len__(self): return len(self.s)
    def __getitem__(self,i):
        a,c=self.s[i]; return {"input_ids":torch.tensor(a),"target_ids":torch.tensor(c)}

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
        pr=model(ii,mk).argmax(-1); m=tg!=-100
        c+=((pr==tg)&m).sum().item(); v+=m.sum().item()
    return c/max(1,v)

def train(cfg):
    set_seed(cfg["seed"])
    device=torch.device("cuda" if (cfg["device"]["use_cuda"] and torch.cuda.is_available()) else "cpu")
    d=cfg["data"]; ml=d["max_seq_length"]; m=cfg["model"]
    tr=DS(d["gen_dir"]+"/train.txt", ml, d.get("gen_cap",0))
    va=DS(d["gen_dir"]+"/val.txt", ml, d.get("val_cap",8000))
    trl=DataLoader(tr,batch_size=cfg["training"]["batch_size"],shuffle=True,collate_fn=collate,
                   num_workers=cfg["device"]["num_workers"],pin_memory=cfg["device"]["pin_memory"])
    val=DataLoader(va,batch_size=cfg["training"]["batch_size"],shuffle=False,collate_fn=collate)
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=m["dropout"],max_position=m["max_position"],pad_id=PAD_ID).to(device)
    print(f"   معاملات: {model.count_parameters():,}")
    crit=nn.CrossEntropyLoss(ignore_index=-100,label_smoothing=cfg["training"].get("label_smoothing",0.0))
    opt=AdamW(model.parameters(),lr=cfg["training"]["learning_rate"],weight_decay=cfg["training"]["weight_decay"])
    accum=cfg["training"]["gradient_accumulation"]; maxs=cfg["training"]["max_steps"]
    sch=cosine(opt,cfg["training"]["warmup_steps"],maxs)
    scaler=torch.amp.GradScaler(enabled=(cfg["device"]["mixed_precision"]=="fp16"))
    out=Path(cfg["logging"]["output_dir"]); out.mkdir(parents=True,exist_ok=True); ei=cfg["logging"]["eval_interval"]
    def save(n,st,acc): torch.save({"model_state":model.state_dict(),"config":cfg,"step":st,"acc":acc,"vocab":"vocab_v2"},out/n)
    print(f"🚀 تدريب كامل — سقف {maxs}\n"); g=0;best=0.0;done=False;model.train()
    while not done:
        for step,b in enumerate(tqdm(trl,desc="تدريب-كامل")):
            ii=b["input_ids"].to(device,non_blocking=True);tg=b["target_ids"].to(device,non_blocking=True);mk=b["attention_mask"].to(device,non_blocking=True)
            with torch.amp.autocast(device_type=device.type,enabled=(device.type=="cuda")):
                lg=model(ii,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES),tg.reshape(-1))/accum
            scaler.scale(loss).backward()
            if (step+1)%accum==0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["training"]["max_grad_norm"])
                scaler.step(opt); scaler.update(); sch.step(); opt.zero_grad(set_to_none=True); g+=1
                if g%ei==0:
                    acc=evaluate(model,val,device); print(f"\n   step {g}: val_acc={acc:.4f}")
                    save("latest.pt",g,acc)
                    if acc>best: best=acc; save("best_model.pt",g,acc); print(f"   ✅ أفضل: {acc:.4f}")
                    model.train()
                if g>=maxs: done=True; break
    save("latest.pt",g,best); print(f"\n✅ انتهى. أفضل val_acc={best:.4f}")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/config_big_full.yaml")
    with open(ap.parse_args().config,encoding="utf-8") as f: cfg=yaml.safe_load(f)
    train(cfg)
