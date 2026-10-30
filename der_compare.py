# -*- coding: utf-8 -*-
"""der_compare.py — مقياسُ DER مستقلٌّ وعادلٌ لمقارنةِ أيِّ مشكِّلَين على نفسِ الذهبيّ.
يحسبُ DER حرفيًّا وكلميًّا تحتَ اصطلاحين:
  موحّد : يتجاهلُ الشدّةَ والسكونَ، ويوحّدُ (أإآٱ→ا، ى→ي، ة→ه).
  عادل  : كالموحّدِ + يتجاهلُ حركةَ آخرِ كلّ كلمة (إعراب)، والألفَ الخنجريّة، والفتحةَ قبلَ الألف.
المحاذاةُ بالحروفِ (نفسُ الإدخالِ المجرّدِ للطرفين). الأرقامُ متطابقةُ المعاملةِ للنموذجين."""
FAT="َ"; DAM="ُ"; KAS="ِ"; TANF="ً"; TAND="ٌ"; TANK="ٍ"
SHAD="ّ"; SUK="ْ"; DAGGER="ٰ"; ALEF="ا"
HARAKAT=set([FAT,DAM,KAS,TANF,TAND,TANK,SHAD,SUK,DAGGER])
_LMAP={"أ":ALEF,"إ":ALEF,"آ":ALEF,"ٱ":ALEF,"ى":"ي","ة":"ه"}
def _nl(c): return _LMAP.get(c,c)
def _pairs(w):
    out=[]
    for ch in w:
        if ch in HARAKAT:
            if out: out[-1][1]+=ch
        else: out.append([_nl(ch),""])
    return out
def _dset(diac, mode, is_last, next_alef):
    s=set(diac); s.discard(SHAD); s.discard(SUK)
    if mode=="fair":
        s.discard(DAGGER)
        if is_last: return frozenset()
        if next_alef: s.discard(FAT)
    return frozenset(s)
def _word_err(gw, pw, mode):
    gp=_pairs(gw); pp=_pairs(pw)
    n=len(gp)
    if len(pp)!=n:                       # عدمُ تطابقِ الحروف (نادرٌ) — احسبِ الأسوأ
        return max(n,len(pp)), max(n,len(pp)), True
    lerr=0
    for i in range(n):
        nxt = (i+1<n and gp[i+1][0]==ALEF)
        last=(i==n-1)
        if _dset(gp[i][1],mode,last,nxt)!=_dset(pp[i][1],mode,last,nxt): lerr+=1
    return n, lerr, (lerr>0)
def der(gold_lines, pred_lines):
    R={"letters":0,"words":0,"skipped":0,
       "lerr_u":0,"lerr_f":0,"werr_u":0,"werr_f":0}
    for g,p in zip(gold_lines, pred_lines):
        gws=g.split(); pws=(p or "").split()
        if len(gws)!=len(pws): R["skipped"]+=1; continue
        for gw,pw in zip(gws,pws):
            nu,eu,wu=_word_err(gw,pw,"unified")
            nf,ef,wf=_word_err(gw,pw,"fair")
            R["letters"]+=nu; R["words"]+=1
            R["lerr_u"]+=eu; R["lerr_f"]+=ef
            R["werr_u"]+= 1 if wu else 0; R["werr_f"]+= 1 if wf else 0
    return R
def report(name, R):
    L=max(1,R["letters"]); W=max(1,R["words"])
    print(f"  {name}:")
    print(f"     DER حرفيّ  — موحّد {100*R['lerr_u']/L:5.2f}%  | عادل {100*R['lerr_f']/L:5.2f}%")
    print(f"     DER كلميّ  — موحّد {100*R['werr_u']/W:5.2f}%  | عادل {100*R['werr_f']/W:5.2f}%")
    print(f"     (حروف {R['letters']} · كلمات {R['words']} · أسطرٌ متخطّاة {R['skipped']})")
