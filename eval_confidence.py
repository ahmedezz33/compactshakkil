# -*- coding: utf-8 -*-
"""
eval_confidence.py — بطاقة ثقة لأيّ نقطة V1 (مفردات 41): للمقارنة قبل/بعد الصقل.

الاستخدام:
    python eval_confidence.py [مسار_النقطة]
افتراضيًّا: compactshakkil_v1_baseline/best_model.pt  (الأساس)
للنموذج المصقول:  python eval_confidence.py outputs_v1_nols/latest.pt

يطبع المقاييس الحاسمة للمقارنة:
  • DER            — الدقّة (يجب ألّا تتدهور)
  • AUROC          — قوّة الفرز (صواب مقابل خطأ) — هذا ما نريد رفعه فوق 0.941
  • ECE خام + T المُثلى + ECE بعد المعايرة — حالة صدق الرقم
  • جدول توجيه معايَر — نقاط التشغيل العمليّة
"""
import sys
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import torch
import torch.nn.functional as F
from models.transformer import CompactShakkilBase
from data.vocab import (split_letters_and_diacritics, encode_chars,
                        PAD_ID, VOCAB_SIZE, NUM_DIACRITIC_CLASSES)

CKPT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "compactshakkil_v1_baseline" / "best_model.pt"
VAL  = ROOT / "data" / "processed" / "val.txt"
TEST = ROOT / "compactshakkil_v1_baseline" / "test.txt"
if not TEST.exists(): TEST = ROOT / "data" / "processed" / "test.txt"
MAX_LEN, BATCH, N_VAL, N_TEST = 300, 64, 3000, 6000


def load_model(device):
    ck = torch.load(str(CKPT), map_location=device, weights_only=False)
    state = ck["model_state"] if isinstance(ck, dict) and "model_state" in ck else \
            (ck["state_dict"] if isinstance(ck, dict) and "state_dict" in ck else ck)
    m = CompactShakkilBase(vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
                           d_model=256, nhead=8, num_encoder_layers=4, dim_feedforward=1024,
                           dropout=0.1, max_position=512, pad_id=PAD_ID).to(device)
    m.load_state_dict(state); m.eval(); return m


def load_samples(path, n):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            letters, cls = split_letters_and_diacritics(line)
            if len(letters) < 3 or len(letters) > MAX_LEN: continue
            out.append((encode_chars(letters), cls))
            if n and len(out) >= n: break
    return sorted(out, key=lambda s: len(s[0]))


def collect(model, samples, device):
    L, T = [], []
    with torch.no_grad():
        for i in range(0, len(samples), BATCH):
            ch = samples[i:i+BATCH]; mx = max(len(a) for a, _ in ch); B = len(ch)
            ii = torch.full((B, mx), PAD_ID, dtype=torch.long)
            tg = torch.full((B, mx), -100, dtype=torch.long)
            mk = torch.zeros((B, mx), dtype=torch.bool)
            for r, (a, c) in enumerate(ch):
                ln = len(a); ii[r,:ln] = torch.tensor(a); tg[r,:ln] = torch.tensor(c); mk[r,:ln] = True
            ii, mk = ii.to(device), mk.to(device); tg = tg.to(device)
            lg = model(ii, mk); v = mk & (tg >= 0)
            L.append(lg[v].cpu()); T.append(tg[v].cpu())
    return torch.cat(L), torch.cat(T)


def ece(conf, correct, M=15):
    e = 0.0; n = conf.numel()
    for b in range(M):
        lo, hi = b/M, (b+1)/M
        sel = (conf >= lo) & (conf < hi) if b < M-1 else (conf >= lo) & (conf <= hi)
        c = sel.sum().item()
        if c: e += (c/n) * abs(conf[sel].mean().item() - correct[sel].float().mean().item())
    return 100.0 * e


def auroc(conf, correct):
    pos, neg = conf[correct], conf[~correct]
    if pos.numel() == 0 or neg.numel() == 0: return float('nan')
    allv = torch.cat([pos, neg]); sv, si = allv.sort()
    ar = torch.arange(1, allv.numel()+1, dtype=torch.double)
    i = 0; n = allv.numel()
    while i < n:
        j = i
        while j+1 < n and sv[j+1] == sv[i]: j += 1
        if j > i: ar[i:j+1] = (i+1 + j+1)/2.0
        i = j+1
    r = torch.empty(n, dtype=torch.double); r[si] = ar
    return (r[:pos.numel()].sum().item() - pos.numel()*(pos.numel()+1)/2.0) / (pos.numel()*neg.numel())


def fit_T(logits, tgt, device):
    vl, vt = logits.to(device), tgt.to(device)
    T = torch.nn.Parameter(torch.ones(1, device=device))
    opt = torch.optim.LBFGS([T], lr=0.05, max_iter=60)
    nll = torch.nn.CrossEntropyLoss()
    def cl(): opt.zero_grad(); l = nll(vl / T.clamp(min=1e-3), vt); l.backward(); return l
    opt.step(cl); return float(T.detach().clamp(min=1e-3).item())


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 80)
    print(f"بطاقة ثقة — {CKPT}")
    print("=" * 80)
    model = load_model(device)
    val_s, test_s = load_samples(VAL, N_VAL), load_samples(TEST, N_TEST)
    print(f"الجهاز={device}  val={len(val_s):,}  test={len(test_s):,}")

    vlog, vtgt = collect(model, val_s, device)
    T = fit_T(vlog, vtgt, device)
    tlog, ttgt = collect(model, test_s, device)
    ps = F.softmax(tlog, dim=-1); conf, pred = ps.max(dim=-1)
    correct = (pred == ttgt); der = 100.0*(~correct).float().mean().item()
    conf_T = F.softmax(tlog / T, dim=-1).max(dim=-1).values

    print(f"\nDER = {der:.2f}%")
    print(f"AUROC (فرز الخطأ) = {auroc(conf, correct):.4f}   ← الأعلى أفضل")
    print(f"T المُثلى = {T:.3f}  ({'شحذ/ناقص ثقة' if T<0.97 else ('تليين/مفرط ثقة' if T>1.03 else 'شبه مضبوط')})")
    print(f"ECE خام = {ece(conf, correct):.3f}%   →   ECE بعد المعايرة = {ece(conf_T, correct):.3f}%")
    print(f"متوسّط الثقة الخام = {conf.mean().item()*100:.2f}%")

    err = ~correct; total = conf.numel(); te = err.sum().item()
    print("\n  توجيه بعتبات معايَرة (T مطبَّقة):")
    print(f"  {'T':>6}{'تغطية':>9}{'DER مقبول':>12}{'مراجعة':>9}{'أخطاء مُلتقطة':>15}")
    for th in [0.90, 0.95, 0.98, 0.99, 0.995]:
        acc = conf_T >= th; na = acc.sum().item(); nr = total-na
        da = 100.0*(err & acc).sum().item()/max(1,na)
        ca = 100.0*(err & ~acc).sum().item()/max(1,te)
        print(f"  {th:>6.3f}{100*na/total:>8.1f}%{da:>11.3f}%{100*nr/total:>8.1f}%{ca:>14.1f}%")

    print("\nللمقارنة: الأساس V1 كان DER=2.38% AUROC=0.941 T=0.67 ECE 8.57%→0.54%.")
    print("إن ارتفع AUROC فوق 0.941 وثبت DER → حذف التنعيم حسّن الفرز فعلًا.")


if __name__ == "__main__":
    out = ROOT / f"eval_confidence_{CKPT.stem}.txt"
    _f = open(out, "w", encoding="utf-8")
    class _T:
        def __init__(s, *x): s.x = x
        def write(s, y):
            for st in s.x:
                try: st.write(y)
                except Exception: pass
        def flush(s):
            for st in s.x:
                try: st.flush()
                except Exception: pass
    sys.stdout = _T(sys.stdout, _f); sys.stderr = sys.stdout
    try: main()
    finally: _f.flush(); _f.close()
