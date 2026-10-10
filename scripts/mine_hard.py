# -*- coding: utf-8 -*-
"""
mine_hard.py — تعدين الأمثلة الصعبة: يجمع جُمل التدريب التي يخطئ فيها النموذج
(ثقة منخفضة + مخالفة للذهبيّ) لإعادة الصقل عليها. الذهبيّ هو المرجع الصحيح.

الاستخدام:
  python scripts/mine_hard.py [ckpt] [in_train.txt] [out_hard.txt] [max_scan] [conf_th]
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from models.transformer import CompactShakkilBase

def load_model(ckpt, dev):
    c=torch.load(ckpt, map_location=dev, weights_only=False); m=c["config"]["model"]
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=0.0,max_position=m["max_position"],pad_id=PAD_ID).to(dev)
    model.load_state_dict(c["model_state"]); model.eval(); return model

@torch.no_grad()
def main():
    ckpt=sys.argv[1] if len(sys.argv)>1 else "outputs_v3_unified/latest.pt"
    inp =sys.argv[2] if len(sys.argv)>2 else "data/processed_clean/train.txt"
    outp=sys.argv[3] if len(sys.argv)>3 else "data/hard_train.txt"
    maxs=int(sys.argv[4]) if len(sys.argv)>4 else 0        # 0 = كامل
    th  =float(sys.argv[5]) if len(sys.argv)>5 else 0.90
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model=load_model(ckpt,dev)
    scanned=hard=err_pos=0
    with open(inp,encoding="utf-8") as f, open(outp,"w",encoding="utf-8") as w:
        for line in f:
            s=line.strip()
            if not s: continue
            L,C=split_letters_and_diacritics(s)
            if len(L)<3 or len(L)>300: continue
            scanned+=1
            if maxs and scanned>maxs: break
            ids=torch.tensor([encode_chars(L)],device=dev); mk=torch.ones_like(ids,dtype=torch.bool)
            p=torch.softmax(model(ids,mk)[0],-1); conf,pred=p.max(-1)
            pred=pred.tolist(); conf=conf.tolist()
            bad=False
            for i in range(len(L)):
                if L[i]==" ": continue
                if pred[i]!=C[i] and conf[i]<th: bad=True; err_pos+=1
            if bad: w.write(s+"\n"); hard+=1
            if scanned%20000==0: print(f"   مُسح {scanned:,} | صعبة {hard:,}")
    print(f"✓ مُسح={scanned:,}  جُمل صعبة={hard:,} ({100*hard/max(1,scanned):.1f}%)  مواضع خطأ مشكوكة={err_pos:,}")
    print(f"  → {outp}")

if __name__=="__main__":
    main()
