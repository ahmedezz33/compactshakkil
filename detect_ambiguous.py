# -*- coding: utf-8 -*-
"""قياسُ حجمِ الطبقةِ الدلاليّةِ وكلفتِها قبلَ التفعيل:
كم كلمةً يكشفُها CAMeL ملتبسةً صوتيًّا (فعلٌ بقراءتين+)؟ وكم استدعاءَ LLM لكلِّ ١٠٠ سطر؟
وأينَ يختلفُ الذهبيُّ عن BERT في تلك الكلماتِ (حيثُ ستنفعُ الطبقةُ فعلًا)؟
يستعملُ bench_gold/bench_pred_ours المحفوظَين (لا GPU) + محلّل CAMeL."""
import sys
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import semantic_layer as S
from camel_snap import _norm, _strip
gold=[l.rstrip("\n") for l in open("bench_gold.txt",encoding="utf-8")]
pred=[l.rstrip("\n") for l in open("bench_pred_ours.txt",encoding="utf-8")]
tot=0; amb=0; amb_lines=0; diff=0; bert_in=0
ex=[]
for g,p in zip(gold,pred):
    gw=g.split(" "); pw=p.split(" ")
    if len(gw)!=len(pw): continue
    line_has=False
    for a,b in zip(gw,pw):
        if _strip(a)!=_strip(b): continue
        tot+=1
        cands=S.ambiguous(b)
        if len(cands)>=2 and _norm(b) in {_norm(c) for c in cands}:
            amb+=1; line_has=True
            bn=_norm(b); gn=_norm(a)
            if bn in {_norm(c) for c in cands}: bert_in+=1
            if bn!=gn:                       # BERT يُخطئُ هنا والذهبيُّ صورةٌ أخرى
                diff+=1
                if len(ex)<20: ex.append((a,b,cands))
    if line_has: amb_lines+=1
nL=sum(1 for g,p in zip(gold,pred) if len(g.split(" "))==len(p.split(" ")))
print("="*62)
print(f"أسطر: {nL} · كلمات: {tot}")
print(f"كلماتٌ ملتبسةٌ (فعلٌ بقراءتين+ لدى CAMeL): {amb}  ({100*amb/max(tot,1):.2f}% من الكلمات)")
print(f"أسطرٌ فيها التباسٌ واحدٌ على الأقلّ        : {amb_lines} ({100*amb_lines/max(nL,1):.1f}%)")
print(f"استدعاءاتُ LLM المتوقّعة لكلِّ ١٠٠ سطر     : ≈ {100*amb/max(nL,1):.1f}")
print("-"*62)
print(f"منها: صورةُ BERT ضمنَ المتنافسات          : {bert_in} ({100*bert_in/max(amb,1):.1f}%)")
print(f"منها: BERT يُخالفُ الذهبيَّ (هنا تنفعُ الطبقةُ): {diff} ({100*diff/max(amb,1):.1f}% من الملتبس)")
print(f"→ السقفُ الأعلى لما قد تُصلِحُه الطبقةُ على هذه العيّنة: {diff} كلمة")
print("="*62)
print("أمثلةُ الملتبسِ الذي يُخطئُه BERT (الذهبيّ | BERT | قراءاتُ CAMeL):")
for a,b,c in ex:
    print(f"   {a:<14} | {b:<14} | {'، '.join(c[:4])}")
print("="*62)
print(f"الطبقةُ مفعّلةٌ الآن؟ {S.enabled()}  (ضعْ semantic_key.txt للتفعيل)")
