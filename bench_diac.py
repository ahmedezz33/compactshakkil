# -*- coding: utf-8 -*-
"""
bench_diac.py — tool-agnostic diacritization benchmark, same metric as your model.

Lets you compare ANY diacritizer (Sadeed, CATT, Claude, Gemini, ...) head-to-head
with your BERT-graft, on the SAME sample and the SAME metric (DER / internal /
final-case), without stopping training. Runs on CPU, touches no GPU.

Workflow (run in a SECOND terminal while training continues):
  1) python bench_diac.py --make-sample 300
        -> writes bench_gold.txt (diacritized) and bench_bare.txt (stripped)
  2) diacritize bench_bare.txt with the other tool -> save as bench_pred.txt
     (one line per input line, same order). For an LLM: paste bench_bare.txt,
     ask it to add full tashkeel, keep line order.
     For YOUR model: run it on bench_bare.txt too, save bench_pred_ours.txt.
  3) python bench_diac.py --score bench_pred.txt --gold bench_gold.txt
        -> prints DER%, internal%, final(i'rab)%  (same numbers as training eval)
"""
import sys, argparse, random
sys.path.insert(0, ".")
from data.vocab_v2 import split_letters_and_diacritics, strip_diacritics


def make_sample(n, src="data/processed_clean/test_noleak.txt"):
    lines = [l.strip() for l in open(src, encoding="utf-8") if l.strip()]
    random.Random(7).shuffle(lines)
    sample = lines[:n]
    with open("bench_gold.txt", "w", encoding="utf-8") as g, \
         open("bench_bare.txt", "w", encoding="utf-8") as b:
        for s in sample:
            g.write(s + "\n")
            b.write(strip_diacritics(s) + "\n")
    print(f"wrote bench_gold.txt and bench_bare.txt ({len(sample)} lines)")


def _final_positions(L):
    """indices that are the last letter of each word (word boundary = space)."""
    fin = set()
    for i, ch in enumerate(L):
        if ch == " ":
            continue
        if i + 1 >= len(L) or L[i + 1] == " ":
            fin.add(i)
    return fin


def score(pred_path, gold_path):
    preds = [l.rstrip("\n") for l in open(pred_path, encoding="utf-8-sig")]
    golds = [l.rstrip("\n") for l in open(gold_path, encoding="utf-8-sig")]
    n = min(len(preds), len(golds))
    tot = err = ft = fe = it = ie = 0
    skipped = 0
    for k in range(n):
        Lg, Cg = split_letters_and_diacritics(golds[k])
        Lp, Cp = split_letters_and_diacritics(preds[k])
        if len(Lg) != len(Lp):        # letter mismatch → can't align this line fairly
            skipped += 1
            continue
        fin = _final_positions(Lg)
        for i in range(len(Lg)):
            if Lg[i] == " ":
                continue
            tot += 1
            isf = i in fin
            if isf: ft += 1
            else: it += 1
            if int(Cg[i]) != int(Cp[i]):
                err += 1
                if isf: fe += 1
                else: ie += 1
    der = 100 * err / max(1, tot)
    internal = 100 * ie / max(1, it)
    final = 100 * fe / max(1, ft)
    print(f"lines scored: {n - skipped} (skipped {skipped} with letter mismatch)")
    print(f"  DER (overall)       = {der:.2f}%")
    print(f"  internal (بنية)     = {internal:.2f}%")
    print(f"  final case (إعراب)  = {final:.2f}%")
    print("  --- your model baseline: DER~2.0  internal~1.72  final~3.01 ---")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-sample", type=int, default=0)
    ap.add_argument("--score", type=str, default="")
    ap.add_argument("--gold", type=str, default="bench_gold.txt")
    a = ap.parse_args()
    if a.make_sample:
        make_sample(a.make_sample)
    elif a.score:
        score(a.score, a.gold)
    else:
        ap.print_help()
