# -*- coding: utf-8 -*-
"""
finetune_diac.py — i'rab-focused fine-tune for the BERT-graft diacritizer.

Targets the model's weak spot: the FINAL (case-ending / i'rab) diacritic, which
errs ~3% vs ~1.7% internal. It up-weights final-position tokens in the loss so
the model learns case endings better. Resumes from the current model, saves to a
SEPARATE dir (never touches the working one), and reports DER / internal / final
before and after so you can see the i'rab error drop.

Data: data/processed_ft/train.txt if present (Tashkeela + Shamela via
merge_corpus.py), else falls back to data/processed_max/train.txt — so it runs
WITHOUT needing OCR first.

    python finetune_diac.py                 # 2 epochs, final_weight=3
    python finetune_diac.py 2 5e-6 4        # epochs, bert_lr, final_weight
"""
import sys, math, random
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / "scripts"))

import torch, torch.nn as nn
from transformers import AutoTokenizer
from data.vocab_v2 import NUM_DIACRITIC_CLASSES
import train_bert_graft as T

RESUME = "outputs_bert_graft/best_model.pt"
OUTDIR = "outputs_bert_graft_ft"
TEST = "data/processed_clean/test_clean.txt"


def _train_path():
    for c in ("data/processed_max/train_clean.txt", "data/processed_ft/train.txt", "data/processed_max/train.txt"):
        if Path(c).exists(): return c
    return "data/processed_max/train.txt"


def _train_sources():
    """مصادرُ تدريبٍ متنوّعة: التشكيلة النظيفة + القرآن النظيف + كتب الشاملة إن وُجدت."""
    import glob
    srcs = [_train_path()]
    if Path("data/processed_quran/quran_clean.txt").exists():
        srcs.append("data/processed_quran/quran_clean.txt")
    srcs += sorted(glob.glob("data/shamela_corpus_clean/*.txt"))  # منظَّفة فقط
    return srcs


def _final_mask(woc):
    """True at the last char of each word (the case-ending position)."""
    fin = torch.zeros_like(woc, dtype=torch.bool)
    fin[:, :-1] = (woc[:, :-1] != -1) & (woc[:, 1:] != woc[:, :-1])
    fin[:, -1] = (woc[:, -1] != -1)
    return fin


def main():
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    bert_lr = float(sys.argv[2]) if len(sys.argv) > 2 else 5e-6
    final_w = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0   # up-weight case endings
    head_lr = bert_lr * 10
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    srcs = _train_sources()
    print(f"i'rab fine-tune | {dev} | epochs={epochs} | bert_lr={bert_lr} | "
          f"final_weight={final_w}")
    print("مصادرُ التدريب:", ", ".join(srcs))

    if not Path(RESUME).exists():
        print(f"no model to resume at {RESUME}."); return

    tok = AutoTokenizer.from_pretrained(T.MODEL_ID)
    model = T.Graft(T.MODEL_ID, T.INIT, dev).to(dev)
    sd = torch.load(RESUME, map_location=dev, weights_only=False)
    model.load_state_dict(sd["model_state"])
    print("resumed full grafted state (base+bert+proj).")

    TASH_CAP = 150000   # عيّنةٌ من التشكيلة تُبقي الصقلَ قصيرًا (يتفادى الانحراف)؛ القرآن/الشاملة كاملًا
    tr = []
    for idx, sp in enumerate(srcs):
        cap = TASH_CAP if idx == 0 else None      # المصدرُ الأوّلُ = التشكيلة الضخمة ← نعيّنُها
        part = T.load(sp, cap, seed=1)
        print(f"   + {sp}: {len(part):,} سطر" + (f" (عيّنة من {TASH_CAP:,})" if cap else ""))
        tr += part
    import random as _r; _r.Random(1).shuffle(tr)
    te = T.load(TEST, 4000, seed=2)
    print(f"train(الكلّ)={len(tr):,} | test={len(te):,}")

    bert_p = list(model.bert.parameters())
    other_p = [p for nm, p in model.named_parameters() if not nm.startswith("bert.")]
    opt = torch.optim.AdamW([{"params": bert_p, "lr": bert_lr},
                             {"params": other_p, "lr": head_lr}], weight_decay=0.01)
    crit = nn.CrossEntropyLoss(ignore_index=-100, reduction="none")   # per-token, we weight it
    scaler = torch.amp.GradScaler(enabled=(dev.type == "cuda"))
    BS = 12
    total = max(1, (len(tr) // BS) * epochs); warm = max(10, total // 20)

    def lr_at(s):
        if s < warm: return s / warm
        p = (s - warm) / max(1, total - warm); return max(0.02, 0.5 * (1 + math.cos(math.pi * p)))
    sch = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)

    out = Path(OUTDIR); out.mkdir(exist_ok=True)
    def save(name): torch.save({"model_state": model.state_dict(), "model_id": T.MODEL_ID}, out / name)

    print("baseline (before fine-tune):")
    best = T.evaluate(model, te, tok, dev)
    EVAL_EVERY = 20000; step = 0
    for ep in range(epochs):
        model.train(); random.shuffle(tr)
        for i in range(0, len(tr), BS):
            batch = tr[i:i + BS]
            ci, woc, attn, enc, nwords, tg = T.collate(batch, tok, dev)
            with torch.amp.autocast(device_type=dev.type, enabled=(dev.type == "cuda")):
                logits = model(ci, woc, attn, enc, nwords, dev)
                per_tok = crit(logits.reshape(-1, NUM_DIACRITIC_CLASSES), tg.reshape(-1))
                # weight: final (case-ending) positions × final_w, valid internal × 1, pad × 0
                valid = (tg.reshape(-1) != -100).float()
                fin = _final_mask(woc).reshape(-1).float()
                w = valid * (1.0 + (final_w - 1.0) * fin)
                loss = (per_tok * w).sum() / w.sum().clamp(min=1.0)
            opt.zero_grad(); scaler.scale(loss).backward()
            scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); sch.step(); step += 1
            if step % 100 == 0:
                print(f"  ep{ep} step{step} loss={loss.item():.3f} lr={sch.get_last_lr()[1]:.2e}")
            if EVAL_EVERY and step % EVAL_EVERY == 0:
                der = T.evaluate(model, te, tok, dev); save("latest.pt")
                if der < best:
                    best = der; save("best_model.pt"); print(f"   improved DER={der:.3f}% saved")
                model.train()
        der = T.evaluate(model, te, tok, dev); save("latest.pt")
        if der < best:
            best = der; save("best_model.pt"); print(f"   improved DER={der:.3f}% saved best_model.pt")
    print(f"done. best overall DER={best:.3f}%  (watch the 'final' number — that's i'rab)")
    print(f"   if the final-ending error dropped: copy {OUTDIR}/best_model.pt over "
          f"outputs_bert_graft/best_model.pt")
    print("   if not: your original model is intact (untouched).")


if __name__ == "__main__":
    main()
