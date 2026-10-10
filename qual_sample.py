# -*- coding: utf-8 -*-
"""
qual_sample.py — اختبار عيّنة عشوائيّة نوعيّ: مُدخَل عارٍ / تشكيل النموذج / المرجع + الأخطاء.
الاستخدام: python qual_sample.py <ckpt> <test.txt> <vocab_module> [n] [seed]
مثال: python qual_sample.py outputs_v1_clean/latest.pt data/processed_clean/test.txt vocab_v1d 15 7
"""
import sys, random, importlib
import numpy as np
sys.path.insert(0, ".")
from load_torch import load_state_dict
from np_eval import build, forward_logits, softmax

def main():
    ckpt, testp, vocab_mod = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 7
    V = importlib.import_module(f"data.{vocab_mod}")
    split, enc, merge, strip = (V.split_letters_and_diacritics, V.encode_chars,
                                V.merge_letters_and_diacritics, V.strip_diacritics)
    CLS = V.DIACRITIC_CLASSES
    sd, _ = load_state_dict(ckpt); M = build(sd)

    lines = []
    with open(testp, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s: continue
            L, C = split(s)
            if 4 <= len(L) <= 120: lines.append(s)   # جمل متوسّطة للعرض
    rnd = random.Random(seed)
    pick = rnd.sample(lines, min(n, len(lines)))
    print("=" * 76)
    print(f"عيّنة عشوائيّة ({len(pick)}) — {ckpt}  [مفردات {vocab_mod}, seed {seed}]")
    print("=" * 76)
    tot = err = exact = 0
    for idx, s in enumerate(pick, 1):
        L, C = split(s); C = list(C)
        pred = softmax(forward_logits(M, np.array(enc(L))), -1).argmax(-1)
        pred_txt = merge(L, list(pred))
        bare = strip(s)
        mism = [(i, L[i], CLS.get(C[i], "?"), CLS.get(int(pred[i]), "?"))
                for i in range(len(L)) if L[i] != " " and int(pred[i]) != C[i]]
        tot += sum(1 for ch in L if ch != " ")
        err += len(mism)
        if not mism: exact += 1
        print(f"\n[{idx}] عارٍ:   {bare}")
        print(f"    مرجع:  {s}")
        print(f"    تنبّؤ:  {pred_txt}")
        if mism:
            det = " ، ".join(f"«{ch}»: مرجع[{g or '∅'}] تنبّؤ[{p or '∅'}]" for _, ch, g, p in mism[:8])
            print(f"    ✗ {len(mism)} خطأ: {det}")
        else:
            print(f"    ✅ مطابق")
    print("\n" + "-" * 76)
    print(f"جمل مطابقة تمامًا: {exact}/{len(pick)}  |  DER العيّنة: {100*err/max(1,tot):.2f}%  ({err}/{tot})")

if __name__ == "__main__":
    main()
