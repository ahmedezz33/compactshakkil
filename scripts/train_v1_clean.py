# -*- coding: utf-8 -*-
"""
train_v1_clean.py — الأساس النظيف (الخطوة ٢): صقل V1-noLS الموسّع (19 فئة)
على البيانات النظيفة التي تُبقي الألف الخنجريّة.

- مفردات: data/vocab_v1d.py (41 حرفًا، 19 فئة، الخنجريّة مُخرَجة).
- انطلاق: compactshakkil_v1_nols/expanded_19.pt (رأس موسّع).
- بيانات: data/processed_clean (مرجع موثوق).
- بلا label_smoothing (نُبقي ميزة الثقة الذاتيّة).

الاستخدام: python scripts/train_v1_clean.py --config configs/base_config_v1_clean.yaml
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
from data.vocab_v1d import (split_letters_and_diacritics, encode_chars,
                            VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from models.transformer import CompactShakkilBase

def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)

def load_config(p):
    with open(p, encoding="utf-8") as f: return yaml.safe_load(f)

class CappedDataset(Dataset):
    def __init__(self, path, max_length, cap):
        self.samples: List[Dict] = []
        print(f"📂 تحميل (حدّ={cap:,}): {path}")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                letters, cls = split_letters_and_diacritics(line)
                if len(letters) < 3 or len(letters) > max_length: continue
                self.samples.append((encode_chars(letters), cls))
                if cap and len(self.samples) >= cap: break
        print(f"   ✓ عيّنات: {len(self.samples):,}")
    def __len__(self): return len(self.samples)
    def __getitem__(self, i):
        a, c = self.samples[i]
        return {"input_ids": torch.tensor(a, dtype=torch.long),
                "target_ids": torch.tensor(c, dtype=torch.long)}

def collate(batch):
    mx = max(len(b["input_ids"]) for b in batch); B = len(batch)
    ii = torch.full((B, mx), PAD_ID, dtype=torch.long)
    tg = torch.full((B, mx), -100, dtype=torch.long)
    mk = torch.zeros((B, mx), dtype=torch.bool)
    for i, b in enumerate(batch):
        L = len(b["input_ids"])
        ii[i,:L]=b["input_ids"]; tg[i,:L]=b["target_ids"]; mk[i,:L]=True
    return {"input_ids": ii, "target_ids": tg, "attention_mask": mk}

def cosine(opt, warm, total):
    def f(s):
        if s < warm: return s/max(1,warm)
        p = (s-warm)/max(1,total-warm); return max(0.0, 0.5*(1+math.cos(math.pi*p)))
    return LambdaLR(opt, f)

@torch.no_grad()
def evaluate(model, loader, device, crit):
    model.eval(); tl=tc=tv=0
    for b in tqdm(loader, desc="تقييم", leave=False):
        ii=b["input_ids"].to(device); tg=b["target_ids"].to(device); mk=b["attention_mask"].to(device)
        with torch.amp.autocast(device_type="cuda", enabled=(device.type=="cuda")):
            lg=model(ii,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES), tg.reshape(-1))
        tl+=loss.item(); pr=lg.argmax(-1); v=tg!=-100
        tc+=((pr==tg)&v).sum().item(); tv+=v.sum().item()
    return {"loss": tl/max(1,len(loader)), "accuracy": tc/tv if tv else 0.0}

def train(cfg):
    set_seed(cfg["seed"])
    device = torch.device("cuda" if (cfg["device"]["use_cuda"] and torch.cuda.is_available()) else "cpu")
    print(f"🖥️ {device} | مفردات={VOCAB_SIZE} فئات={NUM_DIACRITIC_CLASSES}")
    dd = Path(cfg["data"]["processed_dir"]); ml = cfg["data"]["max_seq_length"]
    tr = CappedDataset(str(dd/"train.txt"), ml, cfg["data"]["train_cap"])
    va = CappedDataset(str(dd/"val.txt"), ml, cfg["data"]["val_cap"])
    trl = DataLoader(tr, batch_size=cfg["training"]["batch_size"], shuffle=True,
                     num_workers=cfg["device"]["num_workers"], collate_fn=collate,
                     pin_memory=cfg["device"]["pin_memory"])
    val = DataLoader(va, batch_size=cfg["training"]["batch_size"], shuffle=False,
                     num_workers=cfg["device"]["num_workers"], collate_fn=collate)

    model = CompactShakkilBase(
        vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=cfg["model"]["d_model"], nhead=cfg["model"]["nhead"],
        num_encoder_layers=cfg["model"]["num_encoder_layers"],
        dim_feedforward=cfg["model"]["dim_feedforward"], dropout=cfg["model"]["dropout"],
        max_position=cfg["model"]["max_position"], pad_id=PAD_ID).to(device)
    print(f"   معاملات: {model.count_parameters():,}")

    ic = cfg.get("init_checkpoint")
    if ic and Path(ic).exists():
        ck = torch.load(ic, map_location=device, weights_only=False)
        state = ck["model_state"] if isinstance(ck, dict) and "model_state" in ck else ck
        model.load_state_dict(state)
        print(f"📥 انطلاق من الرأس الموسّع: {ic}")
    else:
        print(f"⚠️ لم أجد init_checkpoint ({ic}) — سيتدرّب من الصفر!")

    crit = nn.CrossEntropyLoss(ignore_index=-100, label_smoothing=cfg["training"]["label_smoothing"])
    opt = AdamW(model.parameters(), lr=cfg["training"]["learning_rate"], weight_decay=cfg["training"]["weight_decay"])
    accum = cfg["training"]["gradient_accumulation"]; maxs = cfg["training"]["max_steps"]
    sch = cosine(opt, cfg["training"]["warmup_steps"], maxs)
    scaler = torch.amp.GradScaler(enabled=(cfg["device"]["mixed_precision"]=="fp16"))
    out = Path(cfg["logging"]["output_dir"]); out.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(out/"tensorboard")
    ei = cfg["logging"]["eval_interval"]; li = cfg["logging"]["log_interval"]
    def save(name, step, vm):
        torch.save({"model_state": model.state_dict(), "config": cfg, "step": step,
                    "val_metrics": vm, "vocab": "vocab_v1d", "num_classes": NUM_DIACRITIC_CLASSES}, out/name)

    base = evaluate(model, val, device, crit)
    print(f"\n🚀 صقل نظيف — سقف {maxs} خطوة، lr={cfg['training']['learning_rate']}")
    print(f"   [أساس step0] val_acc={base['accuracy']:.4f}\n")
    gstep=0; best=0.0; done=False; model.train()
    while not done:
        for step, b in enumerate(tqdm(trl, desc="صقل")):
            ii=b["input_ids"].to(device,non_blocking=True); tg=b["target_ids"].to(device,non_blocking=True)
            mk=b["attention_mask"].to(device,non_blocking=True)
            with torch.amp.autocast(device_type=device.type, enabled=(device.type=="cuda")):
                lg=model(ii,mk); loss=crit(lg.reshape(-1,NUM_DIACRITIC_CLASSES), tg.reshape(-1))/accum
            scaler.scale(loss).backward()
            if (step+1)%accum==0:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["training"]["max_grad_norm"])
                scaler.step(opt); scaler.update(); sch.step(); opt.zero_grad(set_to_none=True); gstep+=1
                if gstep%li==0:
                    writer.add_scalar("train/loss", loss.item()*accum, gstep)
                    writer.add_scalar("train/lr", sch.get_last_lr()[0], gstep)
                if gstep%ei==0:
                    vm=evaluate(model, val, device, crit)
                    print(f"\n   step {gstep}: val_acc={vm['accuracy']:.4f}")
                    writer.add_scalar("val/accuracy", vm["accuracy"], gstep); save("latest.pt", gstep, vm)
                    if vm["accuracy"]>best: best=vm["accuracy"]; save("best_model.pt", gstep, vm); print(f"   ✅ أفضل: {vm['accuracy']:.4f}")
                    model.train()
                if gstep>=maxs: done=True; break
        if not done: done=True
    vm=evaluate(model, val, device, crit); save("latest.pt", gstep, vm)
    print(f"\n✅ انتهى الصقل النظيف عند step {gstep}. val_acc={vm['accuracy']:.4f} (أساس={base['accuracy']:.4f})")
    print(f"   محفوظ: {out/'latest.pt'}")
    writer.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="configs/base_config_v1_clean.yaml")
    train(load_config(ap.parse_args().config))
