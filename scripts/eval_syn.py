# -*- coding: utf-8 -*-
"""
eval_syn.py — يقيس CompactShakkil-Syn على test مع فصل حركة الآخِر عن البنية.
يحتاج: test.txt + test.pos (من morph_extract) + نقطة النموذج النحويّ.
الاستخدام: python scripts/eval_syn.py outputs_syn_pilot/best_model.pt data/processed_clean/test.txt data/processed_clean_pos/test.pos
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from morph_features import NUM_POS, PAD_POS_ID
from models.transformer_syn import CompactShakkilSyn

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
    ck_path=sys.argv[1]; txt=sys.argv[2]; pos=sys.argv[3]
    N=int(sys.argv[4]) if len(sys.argv)>4 else 4000
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck=torch.load(ck_path,map_location=dev,weights_only=False); m=ck["config"]["model"]
    model=CompactShakkilSyn(VOCAB_SIZE,NUM_DIACRITIC_CLASSES,NUM_POS,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=0.0,max_position=m["max_position"],
        pad_id=PAD_ID,pos_pad_id=PAD_POS_ID).to(dev)
    model.load_state_dict(ck["model_state"]); model.eval()
    tot=err=ft=fe=it=ie=seen=0
    with open(txt,encoding="utf-8") as f, open(pos,encoding="utf-8") as g:
        for line,pline in zip(f,g):
            if seen>=N: break
            s=line.strip()
            if not s: continue
            L,C=split_letters_and_diacritics(s)
            p=[int(x) for x in pline.split()]
            if len(p)!=len(L) or len(L)<3 or len(L)>300: continue
            seen+=1
            ii=torch.tensor([encode_chars(L)],dtype=torch.long,device=dev)
            pp=torch.tensor([p],dtype=torch.long,device=dev)
            mk=torch.ones_like(ii,dtype=torch.bool)
            pred=model(ii,pp,mk).argmax(-1)[0].tolist()
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
    print(f"CompactShakkil-Syn — {seen:,} جملة، {tot:,} حرف")
    print(f"  DER كلّيّ           = {100*err/tot:.2f}%   دقّة {100-100*err/tot:.2f}%")
    print(f"  البنية (بلا الآخِر) = {100*ie/it:.2f}%   دقّة {100-100*ie/it:.2f}%")
    print(f"  حركة الآخِر         = {100*fe/ft:.2f}%   دقّة {100-100*fe/ft:.2f}%")
    print("  قارِن بالأساس V3-unified: كلّيّ 2.05% | بنية 1.72% | آخِر 3.01%")

if __name__=="__main__":
    main()
