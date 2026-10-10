# -*- coding: utf-8 -*-
"""
train_graft_large.py — تجربةُ «قاعدةٍ أكبر»: تطعيمُ AraBERT-large v02 (1024 خفيّ، 24 طبقة)
على نموذجِ v3-hard القويّ، تدريبًا على البياناتِ النظيفةِ وتقييمًا على النصِّ النظيف.

معزولٌ تمامًا: يحفظُ في outputs_bert_graft_large/ فلا يمسُّ نموذجَك العامل.
يستأنفُ تلقائيًّا من latest.pt إن وُجد (يأمنُ انقطاعَ التشغيلِ الليليّ).

    python train_graft_large.py            # BS=6, حقبتان (افتراضيّ)
    python train_graft_large.py 3          # BS=3 لو حدثَ نفادُ ذاكرة (OOM)
    python train_graft_large.py 6 3        # BS=6، 3 حقب
"""
import sys, random, math
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
import torch, torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import train_bert_graft as T
from data.vocab_v2 import NUM_DIACRITIC_CLASSES, VOCAB_SIZE, PAD_ID
from models.transformer import CompactShakkilBase

MODEL_ID = "aubmindlab/bert-large-arabertv02"
INIT = "outputs_v3_hard/best_model.pt"
TRAIN = "data/processed_max/train_clean.txt"
TEST = "data/processed_clean/test_clean.txt"
OUTDIR = "outputs_bert_graft_large"
ACCUM = 2                                  # تجميعُ تدرّجٍ (الدفعةُ الفعّالة = BS*ACCUM)


class GL(nn.Module):
    """نفسُ تطعيمِ Graft لكن بأساسِ BERT أكبر وبلا إجبارِ safetensors (كشفٌ تلقائيّ)."""
    def __init__(self, model_id, init_ckpt, dev):
        super().__init__()
        ck = torch.load(init_ckpt, map_location=dev, weights_only=False); m = ck["config"]["model"]
        self.d = m["d_model"]
        self.base = CompactShakkilBase(vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
            d_model=m["d_model"], nhead=m["nhead"], num_encoder_layers=m["num_encoder_layers"],
            dim_feedforward=m["dim_feedforward"], dropout=m["dropout"], max_position=m["max_position"], pad_id=PAD_ID)
        self.base.load_state_dict(ck["model_state"]); print(f"📥 طُعِّم على {init_ckpt}")
        try:
            self.bert = AutoModel.from_pretrained(model_id)
        except Exception as e:
            print("تنبيه: فشلَ التحميلُ العاديّ، أُجرّبُ safetensors:", e)
            self.bert = AutoModel.from_pretrained(model_id, use_safetensors=True)
        print(f"🧠 الأساسُ الأكبر: {model_id} (خفيّ={self.bert.config.hidden_size})")
        self.proj = nn.Linear(self.bert.config.hidden_size, self.d)
        nn.init.normal_(self.proj.weight, std=0.02); nn.init.zeros_(self.proj.bias)

    word_vecs = T.Graft.word_vecs
    forward = T.Graft.forward


def main():
    BS = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    train_path = TRAIN if Path(TRAIN).exists() else "data/processed_max/train.txt"
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"{dev} | BS={BS} acctotal={BS*ACCUM} | حقب={epochs}")
    print(f"تدريب: {train_path} | تقييم: {TEST}")
    if not Path(INIT).exists():
        print(f"❌ لا أساسَ v3-hard في {INIT}"); return
    if not Path(TEST).exists():
        print(f"❌ لا نصَّ اختبارٍ نظيف في {TEST} — شغّلْ run_clean_data.bat أولًا"); return

    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = GL(MODEL_ID, INIT, dev).to(dev)

    out = Path(OUTDIR); out.mkdir(exist_ok=True)
    start_ep = 0
    if (out / "latest.pt").exists():        # استئنافٌ بعد انقطاع
        sd = torch.load(out / "latest.pt", map_location=dev, weights_only=False)
        model.load_state_dict(sd["model_state"]); print("↻ استُؤنِف من latest.pt")

    tr = T.load(train_path, None, seed=1)
    te = T.load(TEST, 6000, seed=2)
    print(f"تدريب={len(tr):,} اختبار={len(te):,}")

    bert_p = list(model.bert.parameters())
    other_p = [p for nm, p in model.named_parameters() if not nm.startswith("bert.")]
    opt = torch.optim.AdamW([{"params": bert_p, "lr": 8e-6}, {"params": other_p, "lr": 1e-4}], weight_decay=0.01)
    crit = nn.CrossEntropyLoss(ignore_index=-100)
    scaler = torch.amp.GradScaler(enabled=(dev.type == "cuda"))
    total = max(1, (len(tr) // BS) * epochs); warm = max(10, total // 20)
    def lr_at(s):
        if s < warm: return s / warm
        p = (s - warm) / max(1, total - warm); return max(0.02, 0.5 * (1 + math.cos(math.pi * p)))
    sch = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)

    def save(name): torch.save({"model_state": model.state_dict(), "model_id": MODEL_ID}, out / name)

    print("— الأساسُ قبلَ التدريبِ (التطعيمُ الطازج) —")
    best = T.evaluate(model, te, tok, dev)
    print(f"   (للمقارنة: نموذجُك الحاليُّ على النظيف ≈ DER 1.10٪ / إعراب 1.40٪)")
    EVAL_EVERY = 20000; step = 0
    for ep in range(start_ep, epochs):
        model.train(); random.shuffle(tr); opt.zero_grad()
        for i in range(0, len(tr), BS):
            batch = tr[i:i + BS]
            ci, woc, attn, enc, nwords, tg = T.collate(batch, tok, dev)
            with torch.amp.autocast(device_type=dev.type, enabled=(dev.type == "cuda")):
                logits = model(ci, woc, attn, enc, nwords, dev)
                loss = crit(logits.reshape(-1, NUM_DIACRITIC_CLASSES), tg.reshape(-1)) / ACCUM
            scaler.scale(loss).backward()
            if ((i // BS) + 1) % ACCUM == 0:
                scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt); scaler.update(); opt.zero_grad()
            sch.step(); step += 1
            if step % 100 == 0:
                print(f"  ep{ep} step{step} loss={loss.item()*ACCUM:.3f} lr={sch.get_last_lr()[1]:.2e}")
            if step % EVAL_EVERY == 0:
                print(f"— تقييمٌ دوريّ (خطوة {step}) —"); der = T.evaluate(model, te, tok, dev); save("latest.pt")
                if der < best: best = der; save("best_model.pt"); print(f"   ✅ أفضل DER={der:.3f}٪ — حُفظ")
                model.train()
        print(f"— تقييمٌ بعدَ الحقبة {ep} —"); der = T.evaluate(model, te, tok, dev); save("latest.pt")
        if der < best: best = der; save("best_model.pt"); print(f"   ✅ أفضل DER={der:.3f}٪ — حُفظ best_model.pt")
    print(f"✅ انتهتِ التجربة. أفضل DER={best:.3f}٪ في {OUTDIR}/")
    print("   قارِنْه بنموذجِك الحاليّ (~1.10٪). إن تفوّقَ بوضوح: ننشرُه؛ وإلّا لا يستحقُّ الحجمَ الأكبر.")


if __name__ == "__main__":
    main()
