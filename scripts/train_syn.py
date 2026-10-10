# -*- coding: utf-8 -*-
"""
train_syn.py — صقل CompactShakkilSyn (نموذج + إشارة POS) انطلاقًا من V3-unified.

مطابقٌ لأنبوب train_v3_unified.py، مع إضافة مجرى POS المُحاذي، ونموذجٍ يدمج
الإشارة النحويّة. يبدأ من أوزان V3-unified (تضمين POS = أصفار ⇒ بدايةٌ مطابقة)،
فأيّ مكسبٍ يُنسَب للإشارة النحويّة وحدها.

الاستخدام: python scripts/train_syn.py --config configs/base_config_syn.yaml
"""
from __future__ import annotations
import argparse, sys, math, random, time
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
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
from morph_features import NUM_POS, PAD_POS_ID
from models.transformer_syn import CompactShakkilSyn

def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)

def load_config(p):
    with open(p, encoding="utf-8") as f: return yaml.safe_load(f)

def read_pair(txt_path, pos_path, max_length, cap=0, repeat=1):
    """يقرأ (chars, pos, classes) من ملفّ نصّ وملفّ POS موازٍ محاذٍ."""
    out=[]
    for _ in range(repeat):
        with open(txt_path,encoding="utf-8") as f, open(pos_path,encoding="utf-8") as g:
            for line, pline in zip(f,g):
                line=line.strip(); pline=pline.strip()
                if not line: continue
                L,C=split_letters_and_diacritics(line)
                if len(L)<3 or len(L)>max_length: continue
                pos=[int(x) for x in pline.split()]
                if len(pos)!=len(L):    # حماية: تجاهل أيّ اختلال محاذاة
                    continue
                out.append((encode_chars(L),C,pos))
                if cap and len(out)>=cap: return out
    return out

class SynDataset(Dataset):
    def __init__(self, gen_txt, gen_pos, quran_txt, quran_pos, max_length,
                 gen_cap, quran_repeat):
        print(f"📂 عامّ (حدّ={gen_cap:,}): {gen_txt}")
        g=read_pair(gen_txt, gen_pos, max_length, cap=gen_cap, repeat=1)[:gen_cap]
        print(f"   عامّ: {len(g):,}")
        q=[]
        if quran_repeat and quran_txt:
            print(f"📂 قرآن (×{quran_repeat}): {quran_txt}")
            q=read_pair(quran_txt, quran_pos, max_length, cap=0, repeat=quran_repeat)
            print(f"   قرآن: {len(q):,}")
        self.samples=g+q; random.shuffle(self.samples)
        print(f"   المزيج: {len(self.samples):,}")
    def __len__(self): return len(self.samples)
    def __getitem__(self,i):
        a,c,p=self.samples[i]
        return {"input_ids":torch.tensor(a,dtype=torch.long),
                "pos_ids":torch.tensor(p,dtype=torch.long),
                "target_ids":torch.tensor(c,dtype=torch.long)}

def collate(batch):
    mx=max(len(b["input_ids"]) for b in batch); B=len(batch)
    ii=torch.full((B,mx),PAD_ID,dtype=torch.long)
    pp=torch.full((B,mx),PAD_POS_ID,dtype=torch.long)
    tg=torch.full((B,mx),-100,dtype=torch.long); mk=torch.zeros((B,mx),dtype=torch.bool)
    for i,b in enumerate(batch):
        L=len(b["input_ids"]); ii[i,:L]=b["input_ids"]; pp[i,:L]=b["pos_ids"]
        tg[i,:L]=b["target_ids"]; mk[i,:L]=True
    return {"input_ids":ii,"pos_ids":pp,"target_ids":tg,"attention_mask":mk}

def cosine(opt,warm,total):
    def f(s):
        if s<warm: return s/max(1,warm)
        p=(s-warm)/max(1,total-warm); return max(0.0,0.5*(1+math.cos(math.pi*p)))
    return LambdaLR(opt,f)

@torch.no_grad()
def evaluate(model,loader,device,crit,use_feat=True):
    model.eval(); tl=tc=tv=0
    for b in tqdm(loader,desc="تقييم",leave=False):
        ii=b["input_ids"].to(device);pp=b["pos_ids"].to(device)
        if not use_feat: pp=torch.zeros_like(pp)
        tg=b["target_ids"].to(device);mk=b["attention_mask"].to(device)
        with torch.amp.autocast(device_type=device.type,enabled=(device.type=="cuda")):
            lg=model(ii,pp,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES),tg.reshape(-1))
        tl+=loss.item(); pr=lg.argmax(-1); v=tg!=-100
        tc+=((pr==tg)&v).sum().item(); tv+=v.sum().item()
    return {"loss":tl/max(1,len(loader)),"accuracy":tc/tv if tv else 0.0}

def train(cfg):
    set_seed(cfg["seed"])
    device=torch.device("cuda" if (cfg["device"]["use_cuda"] and torch.cuda.is_available()) else "cpu")
    USE_FEAT=cfg["data"].get("use_feature",True)   # False = ضابطٌ بلا ميزة (يُصفّر pos)
    print(f"🖥️ {device} | مفردات={VOCAB_SIZE} فئات={NUM_DIACRITIC_CLASSES} POS={NUM_POS} | استعمال الميزة={USE_FEAT}")
    ml=cfg["data"]["max_seq_length"]; d=cfg["data"]
    tr=SynDataset(d["gen_dir"]+"/train.txt", d["gen_pos_dir"]+"/train.pos",
                  d.get("quran_dir","")+"/train.txt" if d.get("quran_repeat") else "",
                  d.get("quran_pos_dir","")+"/train.pos" if d.get("quran_repeat") else "",
                  ml, d["gen_cap"], d.get("quran_repeat",0))
    va=SynDataset(d["gen_dir"]+"/val.txt", d["gen_pos_dir"]+"/val.pos", "","",
                  ml, d["val_cap"], 0)
    trl=DataLoader(tr,batch_size=cfg["training"]["batch_size"],shuffle=True,
                   num_workers=cfg["device"]["num_workers"],collate_fn=collate,pin_memory=cfg["device"]["pin_memory"])
    val=DataLoader(va,batch_size=cfg["training"]["batch_size"],shuffle=False,
                   num_workers=cfg["device"]["num_workers"],collate_fn=collate)
    m=cfg["model"]
    model=CompactShakkilSyn(VOCAB_SIZE, NUM_DIACRITIC_CLASSES, NUM_POS,
        d_model=m["d_model"], nhead=m["nhead"], num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"], dropout=m["dropout"],
        max_position=m["max_position"], pad_id=PAD_ID, pos_pad_id=PAD_POS_ID).to(device)
    print(f"   معاملات: {model.count_parameters():,}")
    ic=cfg.get("init_checkpoint")
    if ic and Path(ic).exists():
        ck=torch.load(ic,map_location=device,weights_only=False)
        base=ck["model_state"] if "model_state" in ck else ck
        n=model.load_base(base); print(f"📥 حُمّل من V3-unified: {n} موتّرًا (POS=أصفار ⇒ بداية مطابقة)")
    else:
        print(f"⚠️ لم أجد init_checkpoint ({ic})!")
    crit=nn.CrossEntropyLoss(ignore_index=-100,label_smoothing=cfg["training"]["label_smoothing"])
    opt=AdamW(model.parameters(),lr=cfg["training"]["learning_rate"],weight_decay=cfg["training"]["weight_decay"])
    accum=cfg["training"]["gradient_accumulation"]; maxs=cfg["training"]["max_steps"]
    sch=cosine(opt,cfg["training"]["warmup_steps"],maxs)
    scaler=torch.amp.GradScaler(enabled=(cfg["device"]["mixed_precision"]=="fp16"))
    out=Path(cfg["logging"]["output_dir"]); out.mkdir(parents=True,exist_ok=True)
    ei=cfg["logging"]["eval_interval"]
    def save(name,step,vm):
        torch.save({"model_state":model.state_dict(),"config":cfg,"step":step,
                    "val_metrics":vm,"vocab":"vocab_v2","arch":"syn","num_pos":NUM_POS},out/name)
    base=evaluate(model,val,device,crit,USE_FEAT)
    print(f"\n🚀 تدريب نحويّ — سقف {maxs} | أساس val_acc={base['accuracy']:.4f}\n")
    gstep=0;best=0.0;done=False;model.train()
    while not done:
        for step,b in enumerate(tqdm(trl,desc="تدريب-نحويّ")):
            ii=b["input_ids"].to(device,non_blocking=True);pp=b["pos_ids"].to(device,non_blocking=True)
            if not USE_FEAT: pp=torch.zeros_like(pp)
            tg=b["target_ids"].to(device,non_blocking=True);mk=b["attention_mask"].to(device,non_blocking=True)
            with torch.amp.autocast(device_type=device.type,enabled=(device.type=="cuda")):
                lg=model(ii,pp,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES),tg.reshape(-1))/accum
            scaler.scale(loss).backward()
            if (step+1)%accum==0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["training"]["max_grad_norm"])
                scaler.step(opt); scaler.update(); sch.step(); opt.zero_grad(set_to_none=True); gstep+=1
                if gstep%ei==0:
                    vm=evaluate(model,val,device,crit,USE_FEAT); print(f"\n   step {gstep}: val_acc={vm['accuracy']:.4f}")
                    save("latest.pt",gstep,vm)
                    if vm["accuracy"]>best: best=vm["accuracy"]; save("best_model.pt",gstep,vm); print(f"   ✅ أفضل: {vm['accuracy']:.4f}")
                    model.train()
                if gstep>=maxs: done=True; break
        # لا نخرج بعد حقبةٍ واحدة — نكرّر الحقبات حتّى بلوغ max_steps
    vm=evaluate(model,val,device,crit,USE_FEAT); save("latest.pt",gstep,vm)
    print(f"\n✅ انتهى التدريب النحويّ عند step {gstep}. val_acc={vm['accuracy']:.4f} (أساس={base['accuracy']:.4f})")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/base_config_syn.yaml")
    train(load_config(ap.parse_args().config))
