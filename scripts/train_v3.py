"""
سكربت تدريب V3 — صقل (Fine-tuning) على القرآن فقط.

يبدأ من أوزان V2 (نفس مفردات 47 رمزًا) ويصقلها على بيانات القرآن.
الهدف: متخصّص قرآنيّ لنظام Reverence-Aware (الحفظ الدقيق مطلوب).

الاستخدام:
    python scripts/train_v3.py --config configs/base_config_v3.yaml
"""

from __future__ import annotations
import argparse
import os
import sys
import math
import random
import time
from pathlib import Path
from typing import Dict, Any

import yaml
import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID
from data.dataset_v2 import get_dataloaders
from models.transformer import CompactShakkilBase


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps):
    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(0.0, 0.5 * (1 + math.cos(math.pi * progress)))
    return LambdaLR(optimizer, lr_lambda)


@torch.no_grad()
def evaluate(model: nn.Module, loader, device: torch.device, criterion) -> Dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_valid = 0
    for batch in tqdm(loader, desc="تقييم", leave=False):
        input_ids = batch["input_ids"].to(device)
        target_ids = batch["target_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        with torch.amp.autocast(device_type="cuda", enabled=(device.type == "cuda")):
            logits = model(input_ids, attention_mask)
            loss = criterion(logits.reshape(-1, NUM_DIACRITIC_CLASSES),
                             target_ids.reshape(-1))
        total_loss += loss.item()
        preds = logits.argmax(dim=-1)
        valid = target_ids != -100
        total_correct += ((preds == target_ids) & valid).sum().item()
        total_valid += valid.sum().item()
    return {
        "loss": total_loss / len(loader),
        "accuracy": total_correct / total_valid if total_valid > 0 else 0.0,
    }


def train(config: Dict[str, Any]) -> None:
    set_seed(config["seed"])

    use_cuda = config["device"]["use_cuda"] and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    print(f"🖥️  الجهاز: {device}")
    if use_cuda:
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    print("\n📦 تحميل بيانات القرآن...")
    loaders = get_dataloaders(
        data_dir=config["data"]["processed_dir"],
        batch_size=config["training"]["batch_size"],
        max_length=config["data"]["max_seq_length"],
        num_workers=config["device"]["num_workers"],
        pin_memory=config["device"]["pin_memory"],
    )
    if "train" not in loaders:
        print("❌ لم أجد بيانات التدريب في", config["data"]["processed_dir"])
        sys.exit(1)

    print("\n🧠 بناء النموذج...")
    model = CompactShakkilBase(
        vocab_size=VOCAB_SIZE,
        num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=config["model"]["d_model"],
        nhead=config["model"]["nhead"],
        num_encoder_layers=config["model"]["num_encoder_layers"],
        dim_feedforward=config["model"]["dim_feedforward"],
        dropout=config["model"]["dropout"],
        max_position=config["model"]["max_position"],
        pad_id=PAD_ID,
    ).to(device)
    print(f"   عدد المعاملات: {model.count_parameters():,}")

    # ═══ صقل من V2: تحميل الأوزان المدرّبة مسبقًا ═══
    init_ckpt = config.get("init_checkpoint")
    if init_ckpt and Path(init_ckpt).exists():
        print(f"\n📥 صقل من checkpoint V2: {init_ckpt}")
        ckpt = torch.load(init_ckpt, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        prev = ckpt.get("val_metrics", {})
        print(f"   ✅ حُمّلت أوزان V2 (val_acc السابق={prev.get('accuracy', '؟')}) — نبدأ الصقل على القرآن")
    else:
        print(f"⚠️ لم أجد init_checkpoint ({init_ckpt}) — سيتدرّب من الصفر!")

    criterion = nn.CrossEntropyLoss(
        ignore_index=-100,
        label_smoothing=config["training"]["label_smoothing"],
    )
    optimizer = AdamW(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )
    total_steps = len(loaders["train"]) * config["training"]["num_epochs"] // \
                  config["training"]["gradient_accumulation"]
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, config["training"]["warmup_steps"], total_steps)

    scaler = torch.amp.GradScaler(enabled=(config["device"]["mixed_precision"] == "fp16"))

    output_dir = Path(config["logging"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(output_dir / "tensorboard")

    print(f"\n🚀 بدء الصقل — {config['training']['num_epochs']} epochs\n")
    global_step = 0
    best_val_acc = 0.0
    accum_steps = config["training"]["gradient_accumulation"]

    for epoch in range(config["training"]["num_epochs"]):
        model.train()
        epoch_loss = 0.0
        epoch_start = time.time()
        pbar = tqdm(loaders["train"], desc=f"Epoch {epoch+1}")
        for step, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            target_ids = batch["target_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(input_ids, attention_mask)
                loss = criterion(logits.reshape(-1, NUM_DIACRITIC_CLASSES),
                                 target_ids.reshape(-1))
                loss = loss / accum_steps

            scaler.scale(loss).backward()
            epoch_loss += loss.item() * accum_steps

            if (step + 1) % accum_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(),
                                               config["training"]["max_grad_norm"])
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1

                if global_step % config["logging"]["log_interval"] == 0:
                    writer.add_scalar("train/loss", loss.item() * accum_steps, global_step)
                    writer.add_scalar("train/lr", scheduler.get_last_lr()[0], global_step)

                if global_step % config["logging"]["eval_interval"] == 0 and "val" in loaders:
                    val_metrics = evaluate(model, loaders["val"], device, criterion)
                    print(f"\n   Step {global_step}: val_loss={val_metrics['loss']:.4f}, "
                          f"val_acc={val_metrics['accuracy']:.4f}")
                    writer.add_scalar("val/loss", val_metrics["loss"], global_step)
                    writer.add_scalar("val/accuracy", val_metrics["accuracy"], global_step)
                    if val_metrics["accuracy"] > best_val_acc:
                        best_val_acc = val_metrics["accuracy"]
                        torch.save({
                            "model_state": model.state_dict(),
                            "config": config,
                            "step": global_step,
                            "val_metrics": val_metrics,
                        }, output_dir / "best_model.pt")
                        print(f"   ✅ حفظ أفضل نموذج قرآنيّ: acc={val_metrics['accuracy']:.4f}")
                    model.train()

            pbar.set_postfix({"loss": f"{loss.item() * accum_steps:.4f}"})

        elapsed = time.time() - epoch_start
        avg_loss = epoch_loss / len(loaders["train"])
        print(f"\n📊 Epoch {epoch+1}/{config['training']['num_epochs']} - "
              f"avg_loss={avg_loss:.4f} - time={elapsed/60:.1f}min\n")

    print("\n✅ اكتمل صقل V3 (متخصّص القرآن)!")
    print(f"   أفضل دقّة قرآنية: {best_val_acc:.4f}")
    print(f"   النموذج محفوظ في: {output_dir / 'best_model.pt'}")
    writer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="صقل CompactShakkil V3 على القرآن")
    parser.add_argument("--config", default="configs/base_config_v3.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    train(config)
