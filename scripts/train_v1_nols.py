# -*- coding: utf-8 -*-
"""
train_v1_nols.py — صقل قصير لـ V1 بحذف label_smoothing (تجربة شحذ الثقة).

يبدأ من أوزان V1 (مفردات 41)، يُعيد تشكيل اللوغيت بخسارة بلا تنعيم، بمعدّل تعلّم
صغير جدًّا وسقف خطوات صارم. لا يمسّ الأصل — يكتب في outputs_v1_nols.
يحفظ best_model.pt (أعلى دقّة) و latest.pt (آخر نقطة) للتقييم بعد التدريب.

الاستخدام:
    python scripts/train_v1_nols.py --config configs/base_config_v1_nols.yaml
"""
from __future__ import annotations
import argparse, sys, math, random, time
from pathlib import Path
from typing import Dict, Any, List

# ترميز UTF-8 لطباعة العربية على ويندوز
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import yaml
import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab import (split_letters_and_diacritics, encode_chars,
                        VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from data.dataset import collate_batch
from models.transformer import CompactShakkilBase


def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class CappedDataset(Dataset):
    """يقرأ أوّل cap سطرًا فقط — يتجنّب تحميل 2GB كاملة لصقل قصير."""
    def __init__(self, file_path: str, max_length: int, cap: int):
        self.samples: List[Dict[str, List[int]]] = []
        print(f"📂 تحميل (حدّ={cap:,}): {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                letters, cls = split_letters_and_diacritics(line)
                if len(letters) < 3 or len(letters) > max_length:
                    continue
                self.samples.append({"input_ids": encode_chars(letters), "target_ids": cls})
                if cap and len(self.samples) >= cap:
                    break
        print(f"   ✓ عيّنات: {len(self.samples):,}")

    def __len__(self): return len(self.samples)

    def __getitem__(self, i):
        s = self.samples[i]
        return {"input_ids": torch.tensor(s["input_ids"], dtype=torch.long),
                "target_ids": torch.tensor(s["target_ids"], dtype=torch.long)}


def get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps):
    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(0.0, 0.5 * (1 + math.cos(math.pi * progress)))
    return LambdaLR(optimizer, lr_lambda)


@torch.no_grad()
def evaluate(model, loader, device, criterion):
    model.eval()
    tl = tc = tv = 0
    for batch in tqdm(loader, desc="تقييم", leave=False):
        input_ids = batch["input_ids"].to(device)
        target_ids = batch["target_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        with torch.amp.autocast(device_type="cuda", enabled=(device.type == "cuda")):
            logits = model(input_ids, attention_mask)
            loss = criterion(logits.reshape(-1, NUM_DIACRITIC_CLASSES), target_ids.reshape(-1))
        tl += loss.item()
        preds = logits.argmax(dim=-1)
        valid = target_ids != -100
        tc += ((preds == target_ids) & valid).sum().item()
        tv += valid.sum().item()
    return {"loss": tl / max(1, len(loader)), "accuracy": tc / tv if tv else 0.0}


def train(config: Dict[str, Any]) -> None:
    set_seed(config["seed"])
    device = torch.device("cuda" if (config["device"]["use_cuda"] and torch.cuda.is_available()) else "cpu")
    print(f"🖥️  الجهاز: {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    data_dir = Path(config["data"]["processed_dir"])
    maxlen = config["data"]["max_seq_length"]
    print("\n📦 تحميل البيانات (بحدّ)...")
    train_ds = CappedDataset(str(data_dir / "train.txt"), maxlen, config["data"]["train_cap"])
    val_ds = CappedDataset(str(data_dir / "val.txt"), maxlen, config["data"]["val_cap"])
    train_loader = DataLoader(train_ds, batch_size=config["training"]["batch_size"], shuffle=True,
                              num_workers=config["device"]["num_workers"], collate_fn=collate_batch,
                              pin_memory=config["device"]["pin_memory"])
    val_loader = DataLoader(val_ds, batch_size=config["training"]["batch_size"], shuffle=False,
                            num_workers=config["device"]["num_workers"], collate_fn=collate_batch)

    print("\n🧠 بناء النموذج...")
    model = CompactShakkilBase(
        vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=config["model"]["d_model"], nhead=config["model"]["nhead"],
        num_encoder_layers=config["model"]["num_encoder_layers"],
        dim_feedforward=config["model"]["dim_feedforward"],
        dropout=config["model"]["dropout"], max_position=config["model"]["max_position"],
        pad_id=PAD_ID).to(device)
    print(f"   معاملات: {model.count_parameters():,}")

    # صقل من V1
    init_ckpt = config.get("init_checkpoint")
    if init_ckpt and Path(init_ckpt).exists():
        print(f"\n📥 صقل من نقطة V1: {init_ckpt}")
        ck = torch.load(init_ckpt, map_location=device, weights_only=False)
        state = ck["model_state"] if isinstance(ck, dict) and "model_state" in ck else ck
        model.load_state_dict(state)
        print("   ✅ حُمّلت أوزان V1 — نبدأ الصقل بلا تنعيم")
    else:
        print("⚠️ لم أجد init_checkpoint — سيتدرّب من الصفر! (أوقف إن لم يكن مقصودًا)")

    criterion = nn.CrossEntropyLoss(ignore_index=-100,
                                    label_smoothing=config["training"]["label_smoothing"])
    optimizer = AdamW(model.parameters(), lr=config["training"]["learning_rate"],
                      weight_decay=config["training"]["weight_decay"])
    accum = config["training"]["gradient_accumulation"]
    max_steps = config["training"]["max_steps"]
    scheduler = get_cosine_schedule_with_warmup(optimizer, config["training"]["warmup_steps"], max_steps)
    scaler = torch.amp.GradScaler(enabled=(config["device"]["mixed_precision"] == "fp16"))

    out = Path(config["logging"]["output_dir"]); out.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(out / "tensorboard")
    eval_int = config["logging"]["eval_interval"]
    log_int = config["logging"]["log_interval"]

    def save(name, step, vm):
        torch.save({"model_state": model.state_dict(), "config": config,
                    "step": step, "val_metrics": vm}, out / name)

    print(f"\n🚀 صقل بلا تنعيم — سقف {max_steps} خطوة، lr={config['training']['learning_rate']}\n")
    gstep = 0; best = 0.0; done = False
    # تقييم أساس قبل الصقل (نقطة انطلاق للمقارنة)
    base_vm = evaluate(model, val_loader, device, criterion)
    print(f"   [أساس step0] val_loss={base_vm['loss']:.4f} val_acc={base_vm['accuracy']:.4f}")
    model.train()

    while not done:
        pbar = tqdm(train_loader, desc=f"صقل")
        for step, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            target_ids = batch["target_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(input_ids, attention_mask)
                loss = criterion(logits.reshape(-1, NUM_DIACRITIC_CLASSES), target_ids.reshape(-1)) / accum
            scaler.scale(loss).backward()

            if (step + 1) % accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config["training"]["max_grad_norm"])
                scaler.step(optimizer); scaler.update(); scheduler.step()
                optimizer.zero_grad(set_to_none=True); gstep += 1

                if gstep % log_int == 0:
                    writer.add_scalar("train/loss", loss.item() * accum, gstep)
                    writer.add_scalar("train/lr", scheduler.get_last_lr()[0], gstep)
                if gstep % eval_int == 0:
                    vm = evaluate(model, val_loader, device, criterion)
                    print(f"\n   step {gstep}: val_loss={vm['loss']:.4f} val_acc={vm['accuracy']:.4f}")
                    writer.add_scalar("val/loss", vm["loss"], gstep)
                    writer.add_scalar("val/accuracy", vm["accuracy"], gstep)
                    save("latest.pt", gstep, vm)
                    if vm["accuracy"] > best:
                        best = vm["accuracy"]; save("best_model.pt", gstep, vm)
                        print(f"   ✅ حفظ أفضل: acc={vm['accuracy']:.4f}")
                    model.train()
                if gstep >= max_steps:
                    done = True; break
            pbar.set_postfix({"loss": f"{loss.item()*accum:.4f}", "step": gstep})
        if not done and gstep < max_steps:
            # نفدت العيّنة قبل السقف — نكتفي
            done = True

    vm = evaluate(model, val_loader, device, criterion)
    save("latest.pt", gstep, vm)
    print(f"\n✅ انتهى الصقل عند step {gstep}. val_acc={vm['accuracy']:.4f} (أساس={base_vm['accuracy']:.4f})")
    print(f"   نقاط محفوظة: {out/'latest.pt'}  و  {out/'best_model.pt'}")
    print("   الآن قيّم الثقة:  python eval_confidence.py outputs_v1_nols/latest.pt")
    writer.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/base_config_v1_nols.yaml")
    args = ap.parse_args()
    train(load_config(args.config))
