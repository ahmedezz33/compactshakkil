# -*- coding: utf-8 -*-
"""
eval_v1d.py — تقييم نموذج 19 فئة (الأساس النظيف) + دقّة الألف الخنجريّة تحديدًا.
الاستخدام: python eval_v1d.py <ckpt> <test.txt> <val.txt> [n_test] [n_val]
"""
import sys
import numpy as np
sys.path.insert(0, ".")
from load_torch import load_state_dict
from np_eval import build, forward_logits, softmax, ece, auroc, fit_T
from data.vocab_v1d import (split_letters_and_diacritics, encode_chars,
                            NUM_DIACRITIC_CLASSES, DIACRITIC_CLASSES)
MAXLEN=300
DAGGER_CLASSES=[15,16,17,18]
NAME={15:"خنجريّة",16:"فتحة+خنجريّة",17:"شدّة+خنجريّة",18:"شدّة+فتحة+خنجريّة"}

def load_samples(path,n):
    out=[]
    with open(path,encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            L,C=split_letters_and_diacritics(line)
            if len(L)<3 or len(L)>MAXLEN: continue
            out.append((encode_chars(L),C))
            if n and len(out)>=n: break
    return out

def run(M,samples):
    conf=[];corr=[];tr=[];pr=[]
    tl=[];tt=[]
    for ids,cls in samples:
        lg=forward_logits(M,np.asarray(ids)); p=softmax(lg,-1)
        pred=p.argmax(-1); c=p.max(-1); cls=np.asarray(cls)
        conf.append(c);corr.append(pred==cls);tr.append(cls);pr.append(pred);tl.append(lg);tt.append(cls)
    return (np.concatenate(conf),np.concatenate(corr),np.concatenate(tr),
            np.concatenate(pr),np.concatenate(tl),np.concatenate(tt))

def main():
    ckpt,testp,valp=sys.argv[1],sys.argv[2],sys.argv[3]
    n_test=int(sys.argv[4]) if len(sys.argv)>4 else 6000
    n_val=int(sys.argv[5]) if len(sys.argv)>5 else 3000
    print("="*66);print(f"تقييم 19 فئة — {ckpt}");print("="*66)
    sd,_=load_state_dict(ckpt); M=build(sd)
    print(f"فئات النموذج: {sd['classifier.3.weight'].shape[0]}")
    val=load_samples(valp,n_val); test=load_samples(testp,n_test)
    _,_,_,_,vlog,vtgt=run(M,val)
    T=fit_T(vlog,vtgt)
    conf,corr,true,pred,tlog,ttgt=run(M,test)
    der=100.0*(~corr).mean()
    confT=softmax(tlog/T,-1).max(-1)
    print(f"\nDER={der:.2f}%  AUROC={auroc(conf,corr):.4f}  T={T:.3f}")
    print(f"ECE خام={ece(conf,corr):.3f}%  →  بعد المعايرة={ece(confT,corr):.3f}%")
    print(f"متوسّط الثقة={conf.mean()*100:.1f}%  | حروف={conf.size:,}")

    print(f"\n[دقّة فئات الألف الخنجريّة]")
    print(f"  {'الفئة':<20}{'دعم(gold)':>10}{'استرجاع':>10}{'دقّة':>9}")
    for c in DAGGER_CLASSES:
        gold=(true==c); predc=(pred==c)
        sup=int(gold.sum())
        rec=100.0*(gold&(pred==true)).sum()/max(1,sup)          # من مواضع gold=c كم أصاب
        prec=100.0*(predc&(pred==true)).sum()/max(1,int(predc.sum()))
        print(f"  {NAME[c]:<20}{sup:>10,}{rec:>9.1f}%{prec:>8.1f}%")
    tot_dagger=sum(int((true==c).sum()) for c in DAGGER_CLASSES)
    hit=sum(int(((true==c)&(pred==true)).sum()) for c in DAGGER_CLASSES)
    print(f"  الإجمالي: مواضع خنجريّة={tot_dagger:,}  استرجاع كلّي={100.0*hit/max(1,tot_dagger):.1f}%")
    print(f"\nمرجع للمقارنة (V1-noLS، 15 فئة، test قديم): DER~2.4% AUROC~0.95 (بلا خنجريّة).")

if __name__=="__main__":
    main()
