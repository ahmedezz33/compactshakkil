# -*- coding: utf-8 -*-
"""
camel_authority_eval.py — قياس جدوى «السلطة الصرفيّة» (مولّد CAMeL) للتشكيل.

لكلّ كلمة في الاختبار نقيس ثلاث صيغ ونقارنها بالذهبيّ:
  • النموذج (v3-hard)
  • CAMeL — أعلى تحليلٍ سياقيّ (MLE)
  • CAMeL — إجماع (كلّ التحاليل الصرفيّة تعطي صيغةً واحدة) ← الأوثق

القرار الحاسم: على مجموعة «الإجماع»، هل CAMeL أدقّ من النموذج؟
إن نعم، فدمجُه كمستوى سلطةٍ في المُوجِّه يرفع الدقّة، وبمقدارٍ نقيسه هنا.

الاستخدام (على جهازك، فيه torch + camel_tools):
  python scripts/camel_authority_eval.py [ckpt] [test.txt] [N]
"""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import torch
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.vocab_v2 import (split_letters_and_diacritics, encode_chars,
                           merge_letters_and_diacritics,
                           VOCAB_SIZE, NUM_DIACRITIC_CLASSES, PAD_ID)
from models.transformer import CompactShakkilBase
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

def load_model(ck, dev):
    c=torch.load(ck, map_location=dev, weights_only=False); m=c["config"]["model"]
    model=CompactShakkilBase(vocab_size=VOCAB_SIZE,num_diacritic_classes=NUM_DIACRITIC_CLASSES,
        d_model=m["d_model"],nhead=m["nhead"],num_encoder_layers=m["num_encoder_layers"],
        dim_feedforward=m["dim_feedforward"],dropout=0.0,max_position=m["max_position"],pad_id=PAD_ID).to(dev)
    model.load_state_dict(c["model_state"]); model.eval(); return model

def spans(L):
    sp=[];st=None
    for i,ch in enumerate(L):
        if ch==" ":
            if st is not None: sp.append((st,i)); st=None
        else:
            if st is None: st=i
    if st is not None: sp.append((st,len(L)))
    return sp

def compare(cand_diac, gold_letters, gold_classes):
    """أرجع (قابلٌ للمقارنة, مطابقةٌ تامّة). قابل = نفس هيكل الحروف."""
    if not cand_diac: return False, False
    Lc, Cc = split_letters_and_diacritics(cand_diac)
    if Lc != gold_letters: return False, False           # هيكلٌ مختلف → غير قابل
    return True, (list(Cc) == list(gold_classes))

@torch.no_grad()
def neural_word_diacs(model, dev, L):
    ids=torch.tensor([encode_chars(L)],device=dev); mk=torch.ones_like(ids,dtype=torch.bool)
    pred=model(ids,mk).argmax(-1)[0].tolist()
    return pred

def main():
    ck = sys.argv[1] if len(sys.argv)>1 else "outputs_v3_hard/best_model.pt"
    testp = sys.argv[2] if len(sys.argv)>2 else "data/processed_clean/test.txt"
    N = int(sys.argv[3]) if len(sys.argv)>3 else 800
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("تحميل النموذج + CAMeL ..."); model=load_model(ck,dev)
    mle = MLEDisambiguator.pretrained()
    an = Analyzer(MorphologyDB.builtin_db())
    # عدّادات
    W=0
    n_comp=n_ok=0                 # النموذج (قابل، مطابق) — على كلّ الكلمات
    top_cov=top_ok=0              # CAMeL top: تغطية قابلة، مطابق
    uni_cov=uni_ok=uni_neural_ok=0  # الإجماع: تغطية، CAMeL مطابق، النموذج مطابق (نفس المجموعة)
    seen=0
    for line in open(testp,encoding="utf-8"):
        if seen>=N: break
        s=line.strip()
        if not s: continue
        L,C=split_letters_and_diacritics(s)
        if len(L)<3 or len(L)>200: continue
        seen+=1
        sp=spans(L)
        toks=["".join(L[a:b]) for a,b in sp]
        if not toks: continue
        npred=neural_word_diacs(model,dev,L)
        disamb=mle.disambiguate(toks)
        for (a,b),tok,dw in zip(sp,toks,disamb):
            gl=L[a:b]; gc=list(C[a:b]); W+=1
            # النموذج
            nd=merge_letters_and_diacritics(gl,[int(npred[i]) for i in range(a,b)])
            c1,o1=compare(nd,gl,gc)
            if c1: n_comp+=1; n_ok+=o1
            # CAMeL top (سياقيّ)
            top = dw.analyses[0].analysis.get("diac") if dw.analyses else None
            c2,o2=compare(top,gl,gc)
            if c2: top_cov+=1; top_ok+=o2
            # CAMeL إجماع (كلّ التحاليل الصرفيّة)
            analyses=an.analyze(tok)
            diacs=set(x.get("diac") for x in analyses if x.get("diac"))
            if len(analyses)>0 and len(diacs)==1:
                ud=next(iter(diacs)); c3,o3=compare(ud,gl,gc)
                if c3:
                    uni_cov+=1; uni_ok+=o3
                    if c1: uni_neural_ok+=o1   # دقّة النموذج على نفس هذه الكلمة
    print("="*66)
    print(f"كلمات={W:,}  (جُمَل={seen:,})")
    print(f"النموذج v3-hard: دقّة الكلمة التامّة = {100*n_ok/max(1,n_comp):.2f}%  (قابل={n_comp:,})")
    print("-"*66)
    print(f"CAMeL — أعلى تحليل سياقيّ (MLE):")
    print(f"  تغطية قابلة = {100*top_cov/max(1,W):.1f}%  |  دقّة الكلمة = {100*top_ok/max(1,top_cov):.2f}%")
    print("-"*66)
    print(f"CAMeL — إجماع (الأوثق):")
    print(f"  تغطية = {100*uni_cov/max(1,W):.1f}% ({uni_cov:,} كلمة)")
    print(f"  دقّة CAMeL على الإجماع  = {100*uni_ok/max(1,uni_cov):.2f}%")
    print(f"  دقّة النموذج على نفسها  = {100*uni_neural_ok/max(1,uni_cov):.2f}%  ← المقارنة الحاسمة")
    diff=100*(uni_ok-uni_neural_ok)/max(1,uni_cov)
    verdict = "CAMeL أدقّ → الدمج يفيد ✅" if diff>0.5 else ("متعادل → لا جدوى تُذكر ⚖️" if abs(diff)<=0.5 else "النموذج أدقّ → لا تدمج ❌")
    print(f"  الفرق (CAMeL − النموذج) = {diff:+.2f} نقطة  →  {verdict}")
    print("="*66)

if __name__=="__main__":
    main()
