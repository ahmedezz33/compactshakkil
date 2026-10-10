# -*- coding: utf-8 -*-
"""
ensemble_eval.py — دمجُ نقاطِ تحقّقٍ بمتوسّطِ الاحتمالات، وقياسُ DER على نصّ الاختبار النظيف.

يقيسُ كلَّ نقطةٍ وحدَها ثمّ الدمجَ، فترى هل يُحسّنُ الدمجُ الدقّةَ فعلًا.
الدمجُ لا يغيّرُ نموذجَك؛ هو قرارُ تصويتٍ وقتَ الاستدلال.

    python ensemble_eval.py                         # الافتراضيّ: المنشور + مخرجا الصقل
    python ensemble_eval.py A.pt B.pt C.pt          # نقاطٌ محدّدة
"""
import sys
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
import torch, torch.nn.functional as Fn
from transformers import AutoTokenizer
import train_bert_graft as T

TEST = "data/processed_clean/test_clean.txt"
N = 6000

def main():
    ckpts = sys.argv[1:] or [
        "outputs_bert_graft/best_model.pt",
        "outputs_bert_graft_ft/best_model.pt",
        "outputs_bert_graft_ft/latest.pt",
    ]
    ckpts = [c for c in ckpts if Path(c).exists()]
    if len(ckpts) < 1:
        print("لا نقاطَ تحقّق."); return
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"{dev} | نقاط: {', '.join(ckpts)}")
    tok = AutoTokenizer.from_pretrained(T.MODEL_ID)

    def load(p):
        m = T.Graft(T.MODEL_ID, T.INIT, dev).to(dev)
        sd = torch.load(p, map_location=dev, weights_only=False)
        m.load_state_dict(sd["model_state"]); m.eval(); return m
    models = [(p, load(p)) for p in ckpts]
    te = T.load(TEST, N, seed=2)
    print(f"اختبار (نظيف) = {len(te):,} سطر\n")

    @torch.no_grad()
    def metric(prob_fn):
        tot=err=ft=fe=it=ie=0; bs=16
        for i in range(0, len(te), bs):
            batch = te[i:i+bs]
            ci,woc,attn,enc,nwords,tg = T.collate(batch, tok, dev)
            pred = prob_fn(ci,woc,attn,enc,nwords).argmax(-1)
            for b,(c,t,w,words) in enumerate(batch):
                n=len(c); fin=set()
                for k in range(n):
                    if w[k]!=-1 and (k+1>=n or w[k+1]!=w[k]): fin.add(k)
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

    def show(name, r): print("  %-40s DER=%.3f%%  بنية=%.3f%%  إعراب=%.3f%%" % (name, *r))
    for p,m in models:
        show(Path(p).parent.name+"/"+Path(p).name, metric(lambda ci,woc,attn,enc,nw, m=m: m(ci,woc,attn,enc,nw,dev)))
    if len(models) >= 2:
        def ens(ci,woc,attn,enc,nw):
            return sum(Fn.softmax(m(ci,woc,attn,enc,nw,dev), dim=-1) for _,m in models)
        show("★ الدمج (متوسّط الاحتمالات)", metric(ens))
    print("\nإن فاز الدمجُ: نستطيعُ تفعيلَه وقتَ الاستدلال (تحميلُ نقطتَين ومتوسّطُهما).")

if __name__ == "__main__":
    main()
