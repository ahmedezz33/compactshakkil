# -*- coding: utf-8 -*-
"""
ensemble_mixed.py — دمجٌ مختلطٌ لنموذجَين بأساسَين مختلفَين (CAMeLBERT + AraBERT-large).
يقرأُ model_id من كلِّ نقطةِ تحقّق، يبني كلَّ نموذجٍ بأساسِه ومُرمِّزِه، ويقيسُ:
كلَّ نموذجٍ وحدَه، ثمّ دمجَهما بأوزانٍ مختلفةٍ (متوسّطُ الاحتمالات) على النصّ النظيف.

لا يمسُّ أيَّ تدريبٍ جارٍ ولا النماذجَ المنشورة — قراءةٌ وتقييمٌ فقط.

    python ensemble_mixed.py
    python ensemble_mixed.py outputs_bert_graft/best_model.pt outputs_bert_graft_large/best_model.pt
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
import torch, torch.nn.functional as Fn
from transformers import AutoTokenizer
import train_bert_graft as T
import train_graft_large as TL     # يحوي GL (تطعيمٌ غيرُ مقيّدٍ بحجمِ الأساس)

TEST = "data/processed_clean/test_clean.txt"
N = 6000

def load_model(ckpt_path, dev):
    ck = torch.load(ckpt_path, map_location=dev, weights_only=False)
    mid = ck.get("model_id") or T.MODEL_ID
    model = TL.GL(mid, T.INIT, dev).to(dev)
    model.load_state_dict(ck["model_state"]); model.eval()
    return model, mid

def main():
    paths = sys.argv[1:] or ["outputs_bert_graft/best_model.pt",
                             "outputs_bert_graft_large/best_model.pt"]
    paths = [p for p in paths if Path(p).exists()]
    if len(paths) < 2:
        print("أحتاجُ نقطتَين موجودتَين. المتوفّر:", paths); return
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"{dev}")
    models = []   # (اسم, model, tok)
    for p in paths:
        m, mid = load_model(p, dev)
        tok = AutoTokenizer.from_pretrained(mid)
        label = Path(p).parent.name
        print(f"📥 {label}: {mid}")
        models.append((label, m, tok))
    te = T.load(TEST, N, seed=2)
    print(f"اختبار (نظيف) = {len(te):,} سطر\n")

    @torch.no_grad()
    def run(weights):
        """weights: قائمةُ أوزانٍ بطولِ النماذج (None = نموذجٌ واحدٌ فقط عند الفهرس الوحيد)."""
        tot=err=ft=fe=it=ie=0; bs=8
        for i in range(0, len(te), bs):
            batch = te[i:i+bs]
            # تنسيقٌ مشترَكٌ للحروف (من النموذج الأوّل)، وenc لكلِّ مُرمِّز
            base_tok = models[0][2]
            ci, woc, attn, enc0, nwords, tg = T.collate(batch, base_tok, dev)
            probs = None
            for (label, m, tok), w in zip(models, weights):
                if w == 0: continue
                enc = enc0 if tok is base_tok else T.collate(batch, tok, dev)[3]
                lg = m(ci, woc, attn, enc, nwords, dev)
                p = Fn.softmax(lg, dim=-1) * w
                probs = p if probs is None else probs + p
            pred = probs.argmax(-1)
            for b,(c,t,wds,words) in enumerate(batch):
                n=len(c); fin=set()
                for k in range(n):
                    if wds[k]!=-1 and (k+1>=n or wds[k+1]!=wds[k]): fin.add(k)
                for k in range(n):
                    if t[k]==-100: continue
                    tot+=1; isf=k in fin
                    if isf: ft+=1
                    else: it+=1
                    if int(pred[b,k])!=t[k]:
                        err+=1
                        if isf: fe+=1
                        else: ie+=1
        return 100*err/tot, 100*ie/it, 100*fe/ft

    def show(name, r): print("  %-34s DER=%.3f%%  بنية=%.3f%%  إعراب=%.3f%%" % (name, *r))
    A = models[0][0]; B = models[1][0]
    show(f"{A} وحدَه", run([1.0, 0.0]))
    show(f"{B} وحدَه", run([0.0, 1.0]))
    print("  — دمجٌ بأوزانٍ مختلفة —")
    for wa in (0.7, 0.6, 0.5, 0.4):
        show(f"دمج  {A}:{wa:.1f} / {B}:{1-wa:.1f}", run([wa, 1-wa]))
    print("\nالحكم: إن لم يَنزِلِ الدمجُ تحتَ أفضلِ نموذجٍ منفردٍ بوضوح → لا يستحقّ كلفةَ أساسَين.")

if __name__ == "__main__":
    main()
