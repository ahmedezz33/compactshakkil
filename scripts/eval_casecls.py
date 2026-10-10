# -*- coding: utf-8 -*-
"""
eval_casecls.py — يقيس دقّة مُصنِّف الحالة في عائلة الآخِر (المقياس الحاسم).
يقارن بحاجز الأساس 97.45%. الاستخدام:
  python scripts/eval_casecls.py outputs_casecls/best_model.pt data/processed_clean/test.txt data/processed_clean_oracle/test.pos
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import split_letters_and_diacritics, encode_chars, VOCAB_SIZE, PAD_ID
from models.transformer import CompactShakkilBase
NUM_CASE=6

def words(L):
    w=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None:w.append((st,i));st=None
        else:
            if st is None:st=i
    if st is not None:w.append((st,len(L)))
    return w

@torch.no_grad()
def main():
    ck=sys.argv[1]; txt=sys.argv[2]; pos=sys.argv[3]; N=int(sys.argv[4]) if len(sys.argv)>4 else 4000
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    c=torch.load(ck,map_location=dev,weights_only=False); m=c["config"]["model"]
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_CASE,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=0.0,max_position=m["max_position"],pad_id=PAD_ID).to(dev)
    model.load_state_dict(c["model_state"]); model.eval()
    fin=correct=seen=0
    with open(txt,encoding="utf-8") as f, open(pos,encoding="utf-8") as g:
        for line,pl in zip(f,g):
            if seen>=N: break
            s=line.strip()
            if not s: continue
            L,_=split_letters_and_diacritics(s)
            fam=[int(x) for x in pl.split()]
            if len(fam)!=len(L) or len(L)<3 or len(L)>300: continue
            seen+=1
            ii=torch.tensor([encode_chars(L)],device=dev); mk=torch.ones_like(ii,dtype=torch.bool)
            pred=model(ii,mk).argmax(-1)[0].tolist()
            for a,b in words(L):
                i=b-1; fin+=1
                if pred[i]==fam[i]: correct+=1
    acc=100*correct/max(1,fin)
    print(f"مُصنِّف الحالة — {seen:,} جملة، {fin:,} نهاية كلمة")
    print(f"  دقّة العائلة (نهاية الكلمة) = {acc:.2f}%")
    print(f"  حاجز الأساس                 = 97.45%")
    print(f"  الفرق = {acc-97.45:+.2f} نقطة  →  {'يتجاوز الحاجز ✅ (يُفيد)' if acc>97.45 else 'لا يتجاوز ❌ (المُدخَل لا يكفي)'}")

if __name__=="__main__":
    main()
