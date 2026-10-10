# -*- coding: utf-8 -*-
"""
normalize_conventions.py — تنظيف اصطلاحيّ آمن: توحيد تسميات متناقضة لا لبس فيها.

قاعدتان عاليتا الأمان (لا تمسّان متجانسًا ولا غموضًا):
  1) لام «ال» قبل حرف قمريّ إن كانت عارية → سكون (الْقَمَر).
  2) كلمات وظيفيّة أحاديّة الصورة: إلى→إِلَى ، إذا→إِذَا ، إذ→إِذْ  (كسرة الهمزة).

لا نمسّ: إن/أن (إِنْ/إِنَّ)، من (مِن/مَن)، على (خنجريّة) — لأنّها متجانسات/غامضة.

الاستخدام (كـ clean_data): python normalize_conventions.py <in_dir> <out_dir>
أو ملفًّا واحدًا:            python normalize_conventions.py <in.txt> <out.txt> file
"""
import sys, os
from pathlib import Path
sys.path.insert(0, ".")
from data.vocab_v2 import (split_letters_and_diacritics, merge_letters_and_diacritics,
                           DIACRITIC_CLASSES)

MOON=set("ابجحخعغفقكمهويأإآء")
SUKUN=4
DIAC2CLS={v:k for k,v in DIACRITIC_CLASSES.items()}
def _cls(diac): return DIAC2CLS.get(diac,0)

# كلمات وظيفيّة: skeleton → فئات قياسيّة (تُشتقّ من الصورة الصحيحة)
def _lex(pairs):
    d={}
    for w in pairs:
        L,C=split_letters_and_diacritics(w); d["".join(L)]=tuple(C)
    return d
FUNC=_lex(["إِلَى","إِذَا","إِذْ"])

def words(L):
    w=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None:w.append((st,i));st=None
        else:
            if st is None:st=i
    if st is not None:w.append((st,len(L)))
    return w

def normalize_line(s):
    L,C=split_letters_and_diacritics(s); C=list(C)
    n_lam=n_func=0
    for a,b in words(L):
        sk="".join(L[a:b])
        # قاعدة 2: كلمة وظيفيّة
        if sk in FUNC and len(FUNC[sk])==(b-a):
            for k,c in enumerate(FUNC[sk]):
                if C[a+k]!=c: C[a+k]=c; n_func+=1
            continue
        # قاعدة 1: لام «ال» قمريّة عارية → سكون
        if b-a>=3 and L[a]=="ا" and L[a+1]=="ل" and L[a+2] in MOON and C[a+1]==0:
            C[a+1]=SUKUN; n_lam+=1
    return merge_letters_and_diacritics(L,C), n_lam, n_func

def process_file(inp,outp):
    lam=func=lines=0
    with open(inp,encoding="utf-8") as f, open(outp,"w",encoding="utf-8") as w:
        for line in f:
            s=line.strip()
            if not s: w.write("\n"); continue
            ns,nl,nf=normalize_line(s); lam+=nl; func+=nf; lines+=1
            w.write(ns+"\n")
    return lines,lam,func

def main():
    a1,a2=sys.argv[1],sys.argv[2]
    mode=sys.argv[3] if len(sys.argv)>3 else "dir"
    if mode=="file":
        lines,lam,func=process_file(a1,a2)
        print(f"سطور={lines:,}  تصحيح لام قمريّة={lam:,}  تصحيح همزة وظيفيّة={func:,}")
    else:
        os.makedirs(a2,exist_ok=True)
        for sp in ["train","val","test"]:
            p=Path(a1)/f"{sp}.txt"
            if not p.exists(): print(f"[{sp}] غير موجود — تجاوز"); continue
            lines,lam,func=process_file(str(p),str(Path(a2)/f"{sp}.txt"))
            print(f"[{sp}] سطور={lines:,}  لام قمريّة={lam:,}  همزة={func:,}  → {Path(a2)/f'{sp}.txt'}")

if __name__=="__main__":
    main()
