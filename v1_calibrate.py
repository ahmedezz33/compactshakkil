# -*- coding: utf-8 -*-
"""
v1_calibrate.py — معايرة الحرارة + مقارنة MC-Dropout لنموذج CompactShakkil V1

يجيب سؤالين:
  (أ) معايرة الحرارة: نُلائم قيمة T واحدة على val تُصلح صدق رقم الثقة (ECE)،
      ونُظهر بأمانة أنّ ترتيب الأخطاء (منحنى المخاطرة/التغطية) لا يتغيّر بها.
  (ب) MC-Dropout: هل يعطي عدمُ اليقين المُجمَّع (K تمريرات بالإسقاط) فصلًا أفضل
      للأخطاء من softmax المفرد؟ نقيس AUROC (صواب مقابل خطأ) و DER المتبقّي
      عند تغطية مُطابَقة (80% / 90%). إن تحسّن → عدم اليقين قابل للتحسين مجّانًا.

يُشغّل من جذر المشروع:  python v1_calibrate.py
"""
import sys, math
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

CKPT = ROOT / "compactshakkil_v1_baseline" / "best_model.pt"
VAL  = ROOT / "data" / "processed" / "val.txt"
TEST = ROOT / "compactshakkil_v1_baseline" / "test.txt"
if not TEST.exists():
    TEST = ROOT / "data" / "processed" / "test.txt"

MAX_LEN = 300
BATCH = 64
N_VAL  = 3000     # جمل لملاءمة الحرارة
N_TEST = 6000     # جمل للتقييم
MC_K   = 8        # تمريرات MC-Dropout


def load_model(device):
    ckpt = torch.load(str(CKPT), map_location=device, weights_only=False)
    state = None
    if isinstance(ckpt, dict):
        for k in ("model_state", "model_state_dict", "state_dict"):
            if k in ckpt: state = ckpt[k]; break
        if state is None and all(isinstance(v, torch.Tensor) for v in ckpt.values()):
            state = ckpt
    model = CompactShakkilBase(
        vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=256, nhead=8, num_encoder_layers=4, dim_feedforward=1024,
        dropout=0.1, max_position=512, pad_id=PAD_ID).to(device)
    model.load_state_dict(state)
    return model


def load_samples(path, n):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            letters, classes = split_letters_and_diacritics(line)
            if len(letters) < 3 or len(letters) > MAX_LEN: continue
            out.append((encode_chars(letters), classes))
            if n and len(out) >= n: break
    return sorted(out, key=lambda s: len(s[0]))


def batches(samples, device):
    for i in range(0, len(samples), BATCH):
        chunk = samples[i:i+BATCH]
        mx = max(len(inp) for inp, _ in chunk); B = len(chunk)
        input_ids = torch.full((B, mx), PAD_ID, dtype=torch.long)
        target = torch.full((B, mx), -100, dtype=torch.long)
        mask = torch.zeros((B, mx), dtype=torch.bool)
        for r, (inp, cls) in enumerate(chunk):
            L = len(inp)
            input_ids[r, :L] = torch.tensor(inp, dtype=torch.long)
            target[r, :L] = torch.tensor(cls, dtype=torch.long)
            mask[r, :L] = True
        yield input_ids.to(device), target.to(device), mask.to(device)


def collect_logits(model, samples, device):
    """يُرجع logits [N,15] وtargets [N] لكل الحروف الصالحة (نموذج في وضع eval)."""
    model.eval()
    L_all, T_all = [], []
    with torch.no_grad():
        for input_ids, target, mask in batches(samples, device):
            logits = model(input_ids, mask)
            valid = mask & (target >= 0)
            L_all.append(logits[valid].cpu())
            T_all.append(target[valid].cpu())
    return torch.cat(L_all), torch.cat(T_all)


def mc_probs(model, samples, device, K):
    """MC-Dropout: متوسّط احتمالات K تمريرات (الإسقاط مُفعّل)."""
    model.train()  # يُفعّل dropout (لا BatchNorm في النموذج)
    sum_p, T_all = [], []
    with torch.no_grad():
        for input_ids, target, mask in batches(samples, device):
            valid = mask & (target >= 0)
            acc = None
            for _ in range(K):
                p = F.softmax(model(input_ids, mask), dim=-1)
                acc = p if acc is None else acc + p
            acc = acc / K
            sum_p.append(acc[valid].cpu()); T_all.append(target[valid].cpu())
    model.eval()
    return torch.cat(sum_p), torch.cat(T_all)


def ece(conf, correct, M=15):
    e = 0.0; n = conf.numel()
    for b in range(M):
        lo, hi = b/M, (b+1)/M
        sel = (conf >= lo) & (conf < hi) if b < M-1 else (conf >= lo) & (conf <= hi)
        c = sel.sum().item()
        if c == 0: continue
        e += (c/n) * abs(conf[sel].mean().item() - correct[sel].float().mean().item())
    return 100.0 * e


def auroc(conf, correct):
    """AUROC لتمييز الصواب من الخطأ عبر الثقة (رتبيّ، بلا sklearn)."""
    pos = conf[correct]; neg = conf[~correct]
    np_, nn_ = pos.numel(), neg.numel()
    if np_ == 0 or nn_ == 0: return float('nan')
    allv = torch.cat([pos, neg])
    order = allv.argsort()
    ranks = torch.empty_like(order, dtype=torch.double)
    ranks[order] = torch.arange(1, allv.numel()+1, dtype=torch.double)
    # متوسّط الرتب للقيم المتساوية
    _, inv, counts = torch.unique(allv, return_inverse=True, return_counts=True)
    csum = torch.zeros(counts.numel()+1, dtype=torch.double)
    # تصحيح التعادل بمتوسّط الرتب
    sorted_vals, sort_idx = allv.sort()
    avg_ranks = torch.arange(1, allv.numel()+1, dtype=torch.double)
    i = 0; n = allv.numel()
    while i < n:
        j = i
        while j+1 < n and sorted_vals[j+1] == sorted_vals[i]:
            j += 1
        if j > i:
            avg_ranks[i:j+1] = (i+1 + j+1) / 2.0
        i = j+1
    r = torch.empty(n, dtype=torch.double); r[sort_idx] = avg_ranks
    sum_pos = r[:np_].sum().item()
    return (sum_pos - np_*(np_+1)/2.0) / (np_*nn_)


def residual_at_coverage(conf, correct, cov):
    """DER المتبقّي لو اعتمدنا آليًّا أعلى (cov) نسبة ثقة."""
    n = conf.numel(); k = int(n*cov)
    if k == 0: return 0.0
    idx = conf.argsort(descending=True)[:k]
    return 100.0 * (~correct[idx]).float().mean().item()


def routing_table(conf, correct, title):
    err = ~correct; total = conf.numel(); total_err = err.sum().item()
    print(f"\n  {title}")
    print(f"  {'العتبة T':>9}{'تغطية':>9}{'DER المقبول':>13}{'حِمل المراجعة':>13}{'الأخطاء المُلتقطة':>17}")
    for T in [0.70, 0.80, 0.90, 0.95, 0.99]:
        acc = conf >= T; rej = ~acc
        na = acc.sum().item(); nr = rej.sum().item()
        der_acc = 100.0*(err & acc).sum().item()/max(1,na)
        caught = 100.0*(err & rej).sum().item()/max(1,total_err)
        print(f"  {T:>9.2f}{100*na/total:>8.1f}%{der_acc:>12.3f}%{100*nr/total:>12.1f}%{caught:>16.1f}%")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 84)
    print("معايرة الحرارة + مقارنة MC-Dropout — CompactShakkil V1")
    print("=" * 84)
    print(f"الجهاز: {device}")
    model = load_model(device)

    print(f"\nتحميل val ({N_VAL}) و test ({N_TEST})…")
    val_s = load_samples(VAL, N_VAL)
    test_s = load_samples(TEST, N_TEST)
    print(f"  val جمل={len(val_s):,}  test جمل={len(test_s):,}")

    # ── (أ) معايرة الحرارة ──
    print("\nملاءمة الحرارة T على val (LBFGS)…")
    val_logits, val_tgt = collect_logits(model, val_s, device)
    vl = val_logits.to(device); vt = val_tgt.to(device)
    T = torch.nn.Parameter(torch.ones(1, device=device))
    opt = torch.optim.LBFGS([T], lr=0.05, max_iter=60)
    nll = torch.nn.CrossEntropyLoss()
    def closure():
        opt.zero_grad(); loss = nll(vl / T.clamp(min=1e-3), vt); loss.backward(); return loss
    opt.step(closure)
    T_opt = float(T.detach().clamp(min=1e-3).item())
    print(f"  T المُثلى = {T_opt:.4f}  ({'شحذ' if T_opt<1 else 'تليين'} — {'النموذج ناقص الثقة' if T_opt<1 else 'مفرط الثقة'})")

    # تقييم على test
    test_logits, test_tgt = collect_logits(model, test_s, device)
    probs_soft = F.softmax(test_logits, dim=-1)
    conf_soft, pred = probs_soft.max(dim=-1)
    correct = (pred == test_tgt)
    der = 100.0*(~correct).float().mean().item()

    probs_temp = F.softmax(test_logits / T_opt, dim=-1)
    conf_temp = probs_temp.max(dim=-1).values  # التنبّؤ نفسه (argmax ثابت)

    print("\n" + "─"*84)
    print("(أ) أثر المعايرة على test")
    print("─"*84)
    print(f"DER = {der:.2f}%  (لا يتغيّر بالحرارة — argmax ثابت)")
    print(f"ECE قبل = {ece(conf_soft, correct):.3f}%   →   ECE بعد = {ece(conf_temp, correct):.3f}%")
    print(f"AUROC (تمييز الخطأ) قبل = {auroc(conf_soft, correct):.4f}   بعد = {auroc(conf_temp, correct):.4f}")
    print("  ← لاحظ: AUROC و DER المتبقّي عند تغطية ثابتة لا يكادان يتغيّران —")
    print("     المعايرة تُصلح صدق الرقم لا قوّة الترتيب. (نقطة أمانة)")
    routing_table(conf_soft, correct, "توجيه بعتبات softmax الخام (قبل المعايرة):")
    routing_table(conf_temp, correct, "توجيه بعتبات مُعايَرة (بعد — العتبات الآن صادقة):")

    # ── (ب) MC-Dropout ──
    print("\n" + "─"*84)
    print(f"(ب) MC-Dropout (K={MC_K} تمريرات) مقابل softmax المفرد")
    print("─"*84)
    print("تشغيل MC-Dropout…")
    p_mc, tgt_mc = mc_probs(model, test_s, device, MC_K)
    conf_mc, pred_mc = p_mc.max(dim=-1)
    correct_mc = (pred_mc == tgt_mc)
    der_mc = 100.0*(~correct_mc).float().mean().item()
    print(f"DER: softmax={der:.2f}%   MC-Dropout={der_mc:.2f}%")
    print(f"AUROC: softmax={auroc(conf_soft, correct):.4f}   MC-Dropout={auroc(conf_mc, correct_mc):.4f}")
    print(f"\n{'التغطية':>9}{'DER متبقٍّ softmax':>20}{'DER متبقٍّ MC':>16}{'التحسّن':>10}")
    for cov in [0.70, 0.80, 0.90, 0.95]:
        r_s = residual_at_coverage(conf_soft, correct, cov)
        r_m = residual_at_coverage(conf_mc, correct_mc, cov)
        print(f"{100*cov:>8.0f}%{r_s:>19.3f}%{r_m:>15.3f}%{r_s-r_m:>+9.3f}")

    print("\n" + "="*84)
    print("الخلاصة")
    print("="*84)
    a_s, a_m = auroc(conf_soft, correct), auroc(conf_mc, correct_mc)
    print(f"• الحرارة المُثلى T={T_opt:.3f} → ECE {ece(conf_soft,correct):.2f}% ثمّ {ece(conf_temp,correct):.2f}% (رقم ثقة صادق).")
    if a_m > a_s + 0.003:
        print(f"• MC-Dropout يحسّن ترتيب الأخطاء (AUROC {a_s:.4f}→{a_m:.4f}) → عدم اليقين قابل للتحسين.")
    else:
        print(f"• MC-Dropout لا يحسّن الترتيب معتدًّا به (AUROC {a_s:.4f} مقابل {a_m:.4f}) →")
        print("  المكسب الحقيقيّ يحتاج تغييرًا تدريبيًّا (حذف label_smoothing) أو تجميع بذور مستقلّة.")


if __name__ == "__main__":
    out = ROOT / "v1_calibrate_output.txt"
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
