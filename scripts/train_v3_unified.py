# -*- coding: utf-8 -*-
"""
train_v3_unified.py — صقل V3 على مزيج (العامّ النظيف + القرآن) لنموذج موحّد للمجالين.

الفكرة: V3 يعرف القرآن بإتقان وجيّد على العامّ. نصقله على البيانات النظيفة العامّة
لرفع كفاءته العامّة، ونخلط القرآن (مُضاعَفًا) كي لا ينساه (تفادي النسيان الكارثيّ).
مفردات vocab_v2 (47 حرفًا، تعرف الخنجريّة). بلا label_smoothing.

الاستخدام: python scripts/train_v3_unified.py --config configs/base_config_v3_unified.yaml
"""
from __future__ import annotations
import argparse, sys, math, random, time
from pathlib import Path
from typing import Dict, Any, List
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import yaml, numpy as np, torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from models.transformer import CompactShakkilBase

def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)

def load_config(p):
    with open(p, encoding="utf-8") as f: return yaml.safe_load(f)

def read_file(path, max_length, cap=0, repeat=1):
    out=[]
    for _ in range(repeat):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                L,C=split_letters_and_diacritics(line)
                if len(L)<3 or len(L)>max_length: continue
                out.append((encode_chars(L),C))
                if cap and len(out)>=cap: return out
    return out

class MixDataset(Dataset):
    def __init__(self, gen_path, quran_path, max_length, gen_cap, quran_repeat):
        self.samples=[]
        print(f"📂 عامّ (حدّ={gen_cap:,}): {gen_path}")
        g=read_file(gen_path, max_length, cap=gen_cap, repeat=1)[:gen_cap]
        print(f"   عامّ: {len(g):,}")
        print(f"📂 قرآن (×{quran_repeat}): {quran_path}")
        q=read_file(quran_path, max_length, cap=0, repeat=quran_repeat)
        print(f"   قرآن: {len(q):,}  ({100*len(q)/max(1,len(g)+len(q)):.0f}% من المزيج)")
        self.samples=g+q
        random.shuffle(self.samples)
        print(f"   المزيج: {len(self.samples):,}")
    def __len__(self): return len(self.samples)
    def __getitem__(self,i):
        a,c=self.samples[i]
        return {"input_ids":torch.tensor(a,dtype=torch.long),
                "target_ids":torch.tensor(c,dtype=torch.long)}

def collate(batch):
    mx=max(len(b["input_ids"]) for b in batch); B=len(batch)
    ii=torch.full((B,mx),PAD_ID,dtype=torch.long); tg=torch.full((B,mx),-100,dtype=torch.long)
    mk=torch.zeros((B,mx),dtype=torch.bool)
    for i,b in enumerate(batch):
        L=len(b["input_ids"]); ii[i,:L]=b["input_ids"]; tg[i,:L]=b["target_ids"]; mk[i,:L]=True
    return {"input_ids":ii,"target_ids":tg,"attention_mask":mk}

def cosine(opt,warm,total):
    def f(s):
        if s<warm: return s/max(1,warm)
        p=(s-warm)/max(1,total-warm); return max(0.0,0.5*(1+math.cos(math.pi*p)))
    return LambdaLR(opt,f)

@torch.no_grad()
def evaluate(model,loader,device,crit):
    model.eval(); tl=tc=tv=0
    for b in tqdm(loader,desc="تقييم",leave=False):
        ii=b["input_ids"].to(device);tg=b["target_ids"].to(device);mk=b["attention_mask"].to(device)
        with torch.amp.autocast(device_type="cuda",enabled=(device.type=="cuda")):
            lg=model(ii,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES),tg.reshape(-1))
        tl+=loss.item(); pr=lg.argmax(-1); v=tg!=-100
        tc+=((pr==tg)&v).sum().item(); tv+=v.sum().item()
    return {"loss":tl/max(1,len(loader)),"accuracy":tc/tv if tv else 0.0}

def train(cfg):
    set_seed(cfg["seed"])
    device=torch.device("cuda" if (cfg["device"]["use_cuda"] and torch.cuda.is_available()) else "cpu")
    print(f"🖥️ {device} | مفردات={VOCAB_SIZE} فئات={NUM_DIACRITIC_CLASSES}")
    ml=cfg["data"]["max_seq_length"]
    tr=MixDataset(cfg["data"]["gen_dir"]+"/train.txt", cfg["data"]["quran_dir"]+"/train.txt",
                  ml, cfg["data"]["gen_cap"], cfg["data"]["quran_repeat"])
    va=MixDataset(cfg["data"]["gen_dir"]+"/val.txt", cfg["data"]["quran_dir"]+"/val.txt",
                  ml, cfg["data"]["val_cap"], 1)
    trl=DataLoader(tr,batch_size=cfg["training"]["batch_size"],shuffle=True,
                   num_workers=cfg["device"]["num_workers"],collate_fn=collate,pin_memory=cfg["device"]["pin_memory"])
    val=DataLoader(va,batch_size=cfg["training"]["batch_size"],shuffle=False,
                   num_workers=cfg["device"]["num_workers"],collate_fn=collate)
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=cfg["model"]["d_model"],nhead=cfg["model"]["nhead"],
        num_encoder_layers=cfg["model"]["num_encoder_layers"],dim_feedforward=cfg["model"]["dim_feedforward"],
        dropout=cfg["model"]["dropout"],max_position=cfg["model"]["max_position"],pad_id=PAD_ID).to(device)
    print(f"   معاملات: {model.count_parameters():,}")
    ic=cfg.get("init_checkpoint")
    if ic and Path(ic).exists():
        ck=torch.load(ic,map_location=device,weights_only=False)
        model.load_state_dict(ck["model_state"] if "model_state" in ck else ck)
        print(f"📥 انطلاق من V3: {ic}")
    else:
        print(f"⚠️ لم أجد init_checkpoint ({ic})!")
    crit=nn.CrossEntropyLoss(ignore_index=-100,label_smoothing=cfg["training"]["label_smoothing"])
    opt=AdamW(model.parameters(),lr=cfg["training"]["learning_rate"],weight_decay=cfg["training"]["weight_decay"])
    accum=cfg["training"]["gradient_accumulation"]; maxs=cfg["training"]["max_steps"]
    sch=cosine(opt,cfg["training"]["warmup_steps"],maxs)
    scaler=torch.amp.GradScaler(enabled=(cfg["device"]["mixed_precision"]=="fp16"))
    out=Path(cfg["logging"]["output_dir"]); out.mkdir(parents=True,exist_ok=True)
    writer=SummaryWriter(out/"tensorboard"); ei=cfg["logging"]["eval_interval"]; li=cfg["logging"]["log_interval"]
    def save(name,step,vm):
        torch.save({"model_state":model.state_dict(),"config":cfg,"step":step,"val_metrics":vm,"vocab":"vocab_v2"},out/name)
    base=evaluate(model,val,device,crit)
    print(f"\n🚀 صقل موحّد — سقف {maxs}، lr={cfg['training']['learning_rate']} | أساس val_acc={base['accuracy']:.4f}\n")
    gstep=0;best=0.0;done=False;model.train()
    while not done:
        for step,b in enumerate(tqdm(trl,desc="صقل")):
            ii=b["input_ids"].to(device,non_blocking=True);tg=b["target_ids"].to(device,non_blocking=True)
            mk=b["attention_mask"].to(device,non_blocking=True)
            with torch.amp.autocast(device_type=device.type,enabled=(device.type=="cuda")):
                lg=model(ii,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES),tg.reshape(-1))/accum
            scaler.scale(loss).backward()
            if (step+1)%accum==0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["training"]["max_grad_norm"])
                scaler.step(opt); scaler.update(); sch.step(); opt.zero_grad(set_to_none=True); gstep+=1
                if gstep%li==0:
                    writer.add_scalar("train/loss",loss.item()*accum,gstep); writer.add_scalar("train/lr",sch.get_last_lr()[0],gstep)
                if gstep%ei==0:
                    vm=evaluate(model,val,device,crit); print(f"\n   step {gstep}: val_acc={vm['accuracy']:.4f}")
                    writer.add_scalar("val/accuracy",vm["accuracy"],gstep); save("latest.pt",gstep,vm)
                    if vm["accuracy"]>best: best=vm["accuracy"]; save("best_model.pt",gstep,vm); print(f"   ✅ أفضل: {vm['accuracy']:.4f}")
                    model.train()
                if gstep>=maxs: done=True; break
        if not done: done=True
    vm=evaluate(model,val,device,crit); save("latest.pt",gstep,vm)
    print(f"\n✅ انتهى الصقل الموحّد عند step {gstep}. val_acc={vm['accuracy']:.4f} (أساس={base['accuracy']:.4f})")
    print(f"   محفوظ: {out/'latest.pt'}")
    writer.close()

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/base_config_v3_unified.yaml")
    train(load_config(ap.parse_args().config))
