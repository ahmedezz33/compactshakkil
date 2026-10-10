# -*- coding: utf-8 -*-
"""Run YOUR current BERT-graft on bench_bare.txt (forced CPU, won't touch training GPU)."""
import sys, os
_R=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _R); sys.path.insert(0, os.path.join(_R, "scripts"))
import torch
from bert_graft_infer import GraftInfer

INF = GraftInfer(device=torch.device("cpu"))     # CPU: training GPU stays free
inp = [l.rstrip("\n") for l in open("bench_bare.txt", encoding="utf-8")]
with open("bench_pred_ours.txt", "w", encoding="utf-8") as out:
    for i, line in enumerate(inp):
        out.write((INF.diacritize(line) if line.strip() else "") + "\n")
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(inp)}")
print(f"done -> bench_pred_ours.txt ({len(inp)} lines)")
