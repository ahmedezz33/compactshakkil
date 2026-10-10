# -*- coding: utf-8 -*-
"""
oracle_case_extract.py — أوراكل حقيقيّ: عائلة الحالة الإعرابيّة من التشكيل الذهبيّ.

لكلّ كلمة، نقرأ حركةَ آخِرها الحقيقيّة ونُسند «عائلة الحالة»:
    مرفوع {ُ ٌ ُّ} → 3 ، منصوب {َ ً َّ} → 4 ، مجرور {ِ ٍ ِّ} → 5 ، غير ذلك (∅/ْ) → 2
ثمّ نبثّها على كلّ أحرف الكلمة (بنفس صيغة .pos ومحاذاتها 1:1).

تسريبٌ مقصودٌ للعائلة الثلاثيّة فقط (لا التنوين/الشدّة/التعريف) ⇒ يقيس السقف الأعلى:
«لو عُرِفت الحالةُ تمامًا، كم تنخفض حركة الآخِر؟». لا يحتاج CAMeL — مشتقٌّ ذاتيًّا.

الاستخدام (كـ morph_extract):
  مجلّد: python oracle_case_extract.py data\processed_clean data\processed_clean_oracle head=220000
  ملف:   python oracle_case_extract.py in.txt out.pos file
"""
import sys, os
from pathlib import Path
sys.path.insert(0, ".")
from data.vocab_v2 import split_letters_and_diacritics

SPACE_ID=1; OTHER_ID=2
NOM={3,7,11}; ACC={1,5,9}; GEN={2,6,10}
def fam_id(cls):
    if cls in NOM: return 3
    if cls in ACC: return 4
    if cls in GEN: return 5
    return OTHER_ID

def _spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp

def line_ids(s):
    L,C=split_letters_and_diacritics(s)
    ids=[SPACE_ID]*len(L)
    for a,b in _spans(L):
        f=fam_id(C[b-1])
        for i in range(a,b): ids[i]=f
    return ids,L

def process_file(inp,outp,limit=0):
    n=read=0
    with open(inp,encoding="utf-8") as f, open(outp,"w",encoding="utf-8") as w:
        for line in f:
            if limit and read>=limit: break
            read+=1
            s=line.strip()
            if not s: w.write("\n"); continue
            ids,_=line_ids(s); w.write(" ".join(map(str,ids))+"\n"); n+=1
    print(f"✓ {inp} → {outp}  ({n:,} سطرًا)")

def _limit(rest):
    for r in rest:
        if r.startswith("head="):
            try: return int(r.split("=")[1])
            except: return 0
    return 0

def main():
    a1,a2=sys.argv[1],sys.argv[2]; rest=sys.argv[3:]
    lim=_limit(rest)
    if "file" in rest:
        process_file(a1,a2,lim)
    else:
        os.makedirs(a2,exist_ok=True)
        for sp in ["train","val","test"]:
            p=Path(a1)/f"{sp}.txt"
            if not p.exists(): print(f"[{sp}] مفقود — تجاوز"); continue
            process_file(str(p), str(Path(a2)/f"{sp}.pos"), lim if sp=="train" else 0)

if __name__=="__main__":
    main()
