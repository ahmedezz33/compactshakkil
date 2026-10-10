# -*- coding: utf-8 -*-
"""
eval_graft.py — يقيس نموذج BERT-graft على ملفّ اختبارٍ بفصل حركة الآخِر.
الاستخدام: python scripts/eval_graft.py data/processed_clean/test_noleak.txt [N]
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import split_letters_and_diacritics
from bert_graft_infer import GraftInfer

def spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp

def main():
    testp=sys.argv[1] if len(sys.argv)>1 else "data/processed_clean/test_noleak.txt"
    N=int(sys.argv[2]) if len(sys.argv)>2 else 4000
    inf=GraftInfer()
    tot=err=ft=fe=it=ie=seen=0
    for line in open(testp,encoding="utf-8"):
        if seen>=N: break
        s=line.strip()
        if not s: continue
        L,C=split_letters_and_diacritics(s)
        if len(L)<3 or len(L)>250: continue
        seen+=1
        Lp,pred=inf._run(s)                 # نفس الحروف + تنبّؤ الفئات
        if len(Lp)!=len(L): continue
        fin={b-1 for a,b in spans(L)}
        for i in range(len(L)):
            if L[i]==" ": continue
            tot+=1; isf=i in fin
            if isf: ft+=1
            else: it+=1
            if int(pred[i])!=int(C[i]):
                err+=1
                if isf: fe+=1
                else: ie+=1
    print(f"BERT-graft على {testp} — {seen:,} جملة، {tot:,} حرف")
    print(f"  DER كلّيّ   = {100*err/tot:.2f}%")
    print(f"  البنية      = {100*ie/it:.2f}%")
    print(f"  حركة الآخِر  = {100*fe/ft:.2f}%")

if __name__=="__main__": main()
