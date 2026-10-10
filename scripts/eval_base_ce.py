# -*- coding: utf-8 -*-
"""eval_base_ce.py — يقيس CompactShakkilBase على test بفصل حركة الآخِر.
الاستخدام: python scripts/eval_base_ce.py <ckpt> data/processed_clean/test.txt [n]"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import split_letters_and_diacritics, encode_chars, VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID
from models.transformer import CompactShakkilBase
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
    ck=sys.argv[1]; txt=sys.argv[2]; N=int(sys.argv[3]) if len(sys.argv)>3 else 4000
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    c=torch.load(ck,map_location=dev,weights_only=False); m=c["config"]["model"]
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=0.0,max_position=m["max_position"],pad_id=PAD_ID).to(dev)
    model.load_state_dict(c["model_state"]); model.eval()
    tot=err=ft=fe=it=ie=seen=0
    for line in open(txt,encoding="utf-8"):
        if seen>=N: break
        s=line.strip()
        if not s: continue
        L,C=split_letters_and_diacritics(s)
        if len(L)<3 or len(L)>300: continue
        seen+=1
        ii=torch.tensor([encode_chars(L)],device=dev); mk=torch.ones_like(ii,dtype=torch.bool)
        pred=model(ii,mk).argmax(-1)[0].tolist()
        fin={b-1 for a,b in words(L)}
        for i in range(len(L)):
            if L[i]==" ": continue
            tot+=1; isf=i in fin
            if isf: ft+=1
            else: it+=1
            if pred[i]!=C[i]:
                err+=1
                if isf: fe+=1
                else: ie+=1
    print(f"{ck} — {seen:,} جملة، {tot:,} حرف")
    print(f"  DER كلّيّ   = {100*err/tot:.2f}%")
    print(f"  البنية      = {100*ie/it:.2f}%")
    print(f"  حركة الآخِر  = {100*fe/ft:.2f}%")
    print(f"  الأساس V3-unified: DER 2.05 | بنية 1.72 | آخِر 3.01")
if __name__=="__main__":
    main()
