# -*- coding: utf-8 -*-
"""
v1_confidence_test.py — تجربة معايرة الثقة لنموذج CompactShakkil V1

السؤال: هل يتركّز خطأ V1 في التنبّؤات منخفضة الثقة؟
إن كان كذلك → ثقة Softmax إشارة صالحة لتوجيه "المؤكّد يُعتمد، المشكوك يُراجع".

المنهج:
  1) نُشغّل V1 على عيّنة من مجموعة الاختبار (نفس تقسيم التدريب).
  2) لكل حرف: نأخذ Softmax على المخرجات [15]، فالفئة = argmax، والثقة = أعلى احتمال.
  3) نقارن التنبّؤ بالهدف، ونُصنّف الحروف حسب مستوى الثقة.
  4) نقيس معدّل الخطأ في كل شريحة ثقة + منحنى التوجيه (تغطية مقابل خطأ متبقٍّ).

يُشغّل من جذر المشروع:  python v1_confidence_test.py [عدد_الجمل]
الافتراضي: 8000 جملة (سريع ودالّ إحصائيًّا). مرّر 0 لكامل المجموعة.
"""
import sys, os, math
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F
from models.transformer import CompactShakkilBase
from data.vocab import (
    split_letters_and_diacritics, encode_chars,
    PAD_ID, VOCAB_SIZE, NUM_DIACRITIC_CLASSES, DIACRITIC_CLASSES,
)

CKPT = ROOT / "compactshakkil_v1_baseline" / "best_model.pt"
TEST = ROOT / "compactshakkil_v1_baseline" / "test.txt"
if not TEST.exists():
    TEST = ROOT / "data" / "processed" / "test.txt"

MAX_LEN = 300
BATCH = 64
N_SENT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000  # 0 = الكل


def load_model(device):
    ckpt = torch.load(str(CKPT), map_location=device, weights_only=False)
    # استخراج أوزان النموذج مهما كان مفتاح الحفظ
    state = None
    if isinstance(ckpt, dict):
        for k in ("model_state", "model_state_dict", "state_dict"):
            if k in ckpt:
                state = ckpt[k]; break
        if state is None and all(isinstance(v, torch.Tensor) for v in ckpt.values()):
            state = ckpt
    if state is None:
        raise RuntimeError("تعذّر إيجاد أوزان النموذج في checkpoint")
    # أبعاد النموذج من config.yaml المعروفة (مثبّتة في INFO.txt)
    model = CompactShakkilBase(
        vocab_size=VOCAB_SIZE, num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=256, nhead=8, num_encoder_layers=4, dim_feedforward=1024,
        dropout=0.1, max_position=512, pad_id=PAD_ID,
    ).to(device)
    model.load_state_dict(state)
    model.eval()
    return model


def load_samples(n):
    samples = []
    with open(TEST, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            letters, classes = split_letters_and_diacritics(line)
            if len(letters) < 3 or len(letters) > MAX_LEN:
                continue
            samples.append((encode_chars(letters), classes))
            if n and len(samples) >= n:
                break
    return samples


def run(model, samples, device):
    """يُرجع مصفوفتين: ثقة كل حرف (max softmax) وصوابه (0/1)."""
    confs, corrects = [], []
    # ترتيب حسب الطول لكفاءة الحشو
    samples = sorted(samples, key=lambda s: len(s[0]))
    with torch.no_grad():
        for i in range(0, len(samples), BATCH):
            chunk = samples[i:i + BATCH]
            mx = max(len(inp) for inp, _ in chunk)
            B = len(chunk)
            input_ids = torch.full((B, mx), PAD_ID, dtype=torch.long)
            target = torch.full((B, mx), -100, dtype=torch.long)
            mask = torch.zeros((B, mx), dtype=torch.bool)
            for r, (inp, cls) in enumerate(chunk):
                L = len(inp)
                input_ids[r, :L] = torch.tensor(inp, dtype=torch.long)
                target[r, :L] = torch.tensor(cls, dtype=torch.long)
                mask[r, :L] = True
            input_ids, mask = input_ids.to(device), mask.to(device)
            logits = model(input_ids, mask)              # [B, T, 15]
            probs = F.softmax(logits, dim=-1)
            conf, pred = probs.max(dim=-1)               # [B, T]
            valid = mask & (target.to(device) >= 0)
            tgt = target.to(device)
            corr = (pred == tgt) & valid
            confs.append(conf[valid].cpu())
            corrects.append(corr[valid].cpu())
    return torch.cat(confs), torch.cat(corrects)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 84)
    print("تجربة معايرة الثقة — CompactShakkil V1")
    print("=" * 84)
    print(f"الجهاز: {device} | checkpoint: {CKPT.name} | اختبار: {TEST}")
    print(f"مفردات={VOCAB_SIZE}  فئات الحركة={NUM_DIACRITIC_CLASSES}")

    model = load_model(device)
    n_params = model.count_parameters()
    print(f"معاملات النموذج: {n_params:,}")

    print(f"\nتحميل العيّنات (حدّ={'الكل' if N_SENT == 0 else N_SENT} جملة)…")
    samples = load_samples(N_SENT)
    n_chars = sum(len(s[1]) for s in samples)
    print(f"  جمل={len(samples):,}  حروف≈{n_chars:,}")

    print("الاستدلال…")
    conf, corr = run(model, samples, device)
    total = conf.numel()
    err = (~corr)
    overall_der = 100.0 * err.sum().item() / total
    mean_conf = conf.mean().item()
    print(f"\nإجمالي الحروف المقيسة: {total:,}")
    print(f"DER الكلّي (كل الحروف): {overall_der:.2f}%   |   متوسّط الثقة: {mean_conf*100:.2f}%")

    # ── جدول 1: شرائح الثقة ──
    print("\n" + "─" * 84)
    print("جدول 1 — معدّل الخطأ حسب شريحة الثقة")
    print("─" * 84)
    edges = [1.01, 0.999, 0.99, 0.95, 0.90, 0.80, 0.70, 0.50, 0.0]
    labels = ["≥0.999", "0.99–0.999", "0.95–0.99", "0.90–0.95",
              "0.80–0.90", "0.70–0.80", "0.50–0.70", "<0.50"]
    print(f"{'شريحة الثقة':<14}{'الحروف':>12}{'% من الكل':>12}{'أخطاء':>10}{'خطأ الشريحة':>14}{'% من كل الأخطاء':>18}")
    total_err = err.sum().item()
    for j, lab in enumerate(labels):
        hi, lo = edges[j], edges[j + 1]
        sel = (conf < hi) & (conf >= lo)
        c = sel.sum().item()
        if c == 0:
            print(f"{lab:<14}{0:>12}{'—':>12}{0:>10}{'—':>14}{'—':>18}")
            continue
        e = (err & sel).sum().item()
        print(f"{lab:<14}{c:>12,}{100*c/total:>11.2f}%{e:>10,}{100*e/c:>13.2f}%{100*e/max(1,total_err):>17.2f}%")

    # ── جدول 2: منحنى التوجيه (عتبة القبول) ──
    print("\n" + "─" * 84)
    print("جدول 2 — التوجيه بعتبة: اقبل conf≥T آليًّا، أحِل الباقي للمراجعة")
    print("─" * 84)
    print(f"{'العتبة T':>10}{'مقبول آليًّا':>14}{'تغطية':>10}{'DER المقبول':>14}{'حِمل المراجعة':>14}{'DER المُحال':>14}{'الأخطاء المُلتقطة':>18}")
    for T in [0.50, 0.70, 0.80, 0.90, 0.95, 0.99, 0.995, 0.999]:
        acc = conf >= T
        rej = ~acc
        na, nr = acc.sum().item(), rej.sum().item()
        der_acc = 100.0 * (err & acc).sum().item() / max(1, na)
        der_rej = 100.0 * (err & rej).sum().item() / max(1, nr)
        caught = 100.0 * (err & rej).sum().item() / max(1, total_err)  # % من الأخطاء داخل المراجعة
        print(f"{T:>10.3f}{na:>14,}{100*na/total:>9.1f}%{der_acc:>13.3f}%{100*nr/total:>13.1f}%{der_rej:>13.2f}%{caught:>17.1f}%")

    # ── معايرة: ECE ──
    print("\n" + "─" * 84)
    print("معايرة الثقة (ECE) — هل الثقة تُطابق الصواب الفعليّ؟")
    print("─" * 84)
    M = 10
    ece = 0.0
    print(f"{'حزمة الثقة':<14}{'الحروف':>12}{'ثقة متوسّطة':>14}{'دقّة فعلية':>14}{'الفجوة':>10}")
    for b in range(M):
        lo, hi = b / M, (b + 1) / M
        sel = (conf >= lo) & (conf < hi) if b < M - 1 else (conf >= lo) & (conf <= hi)
        c = sel.sum().item()
        if c == 0:
            continue
        avg_conf = conf[sel].mean().item()
        acc = corr[sel].float().mean().item()
        gap = abs(avg_conf - acc)
        ece += (c / total) * gap
        print(f"{f'{lo:.1f}–{hi:.1f}':<14}{c:>12,}{avg_conf*100:>13.2f}%{acc*100:>13.2f}%{gap*100:>9.2f}%")
    print(f"\nECE (خطأ المعايرة المتوقّع): {ece*100:.3f}%")

    # ── الخلاصة ──
    print("\n" + "=" * 84)
    print("الخلاصة")
    print("=" * 84)
    # مقارنة: DER عند قبول 90% الأعلى ثقة مقابل الكلّي
    T90 = torch.quantile(conf, 0.10).item()  # عتبة تُبقي أعلى 90% ثقة
    acc90 = conf >= T90
    der90 = 100.0 * (err & acc90).sum().item() / max(1, acc90.sum().item())
    print(f"لو اعتمدنا أعلى 90% ثقة تلقائيًّا (T≈{T90:.3f}): DER المقبول = {der90:.3f}% "
          f"(مقابل {overall_der:.2f}% كلّي).")
    print("إن كان DER المقبول ≪ الكلّي وحِمل مراجعة صغير يلتقط أغلب الأخطاء → الثقة إشارة توجيه صالحة.")


if __name__ == "__main__":
    out = ROOT / "v1_confidence_output.txt"
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
    try:
        main()
    finally:
        _f.flush(); _f.close()
