# -*- coding: utf-8 -*-
"""الاختبارُ الحاسم: CAMeL أساسٌ + BERT لما لا يُحسَم، بقياسٍ يُحيِّدُ كلَّ اصطلاحاتِ CAMeL
(حركةُ الآخِر/الوقف + الألفُ الخنجريّة + الفتحةُ قبلَ مدٍّ هموجينيّ). المحلّلُ وحدَه بلا MLE.
فإن بقيَ CAMeL يُفسِدُ أكثرَ ممّا يُصلِحُ هنا، فالعجزُ لغويٌّ لا اصطلاحيّ."""
import sys, os, random, functools, io, re
N=int(os.environ.get("BENCH_N","3000")); OUT="eval_report_base.txt"
buf=io.StringIO()
def P(*a):
    s=" ".join(str(x) for x in a); print(s); buf.write(s+"\n")
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
P(f"… BERT + محلّل CAMeL الصرفيّ (بلا MLE) — تحييدُ كلِّ الاصطلاح — عيّنة={N}")
import app_teach as A
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_snap import _norm, _strip
from data.vocab_v2 import strip_diacritics
an=Analyzer(MorphologyDB.builtin_db())

_WAQF=re.compile(r'[ًٌٍَُِ]([اوىي]?)$')
def _conv(s):                       # s مُطبَّعٌ بـ_norm؛ نُحيِّدُ اصطلاحاتِ CAMeL كلَّها
    s=_WAQF.sub(r'\1', s)           # حركةُ الآخِر (الوقف)
    s=s.replace('ٰ','')            # الألفُ الخنجريّة
    s=re.sub(r'َ(?=ا)','',s)        # فتحةٌ قبلَ ألف
    s=re.sub(r'ِ(?=ي)','',s)        # كسرةٌ قبلَ ياءِ مدّ
    s=re.sub(r'ُ(?=و)','',s)        # ضمّةٌ قبلَ واوِ مدّ
    return s

@functools.lru_cache(maxsize=400000)
def _analyses(bare):
    try: raw=tuple(sorted({a['diac'] for a in an.analyze(bare) if a.get('diac')}))
    except Exception: raw=tuple()
    bykey={}
    for x in raw: bykey.setdefault(_conv(_norm(x)), x)
    return raw, bykey

lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(13).shuffle(lines); lines=lines[:N]
tot=0; skip=0; e_bert=0; e_cb=0
resolved=0; passed=0; r_correct=0; cb_fix=0; cb_break=0
errB=0; gold_unique=0; gold_in=0; both=0; illegal=0; unknown=0
ex_fix=[]; ex_break=[]
for gold in lines:
    gws=gold.split(" ")
    pb=A.INF.diacritize(strip_diacritics(gold)); pws=pb.split(" ")
    if len(pws)!=len(gws): skip+=1; continue
    tot+=len(gws)
    for i,gw in enumerate(gws):
        bare=_strip(pws[i])
        gK=_conv(_norm(gw)); bK=_conv(_norm(pws[i]))
        raw,bykey=_analyses(bare)
        if len(bykey)==1:
            resolved+=1; onlyk=next(iter(bykey)); outK=onlyk; raw0=bykey[onlyk]
            if onlyk==gK: r_correct+=1
            if onlyk!=bK:
                if onlyk==gK and bK!=gK:
                    cb_fix+=1
                    if len(ex_fix)<18: ex_fix.append((gw,pws[i],raw0))
                elif onlyk!=gK and bK==gK:
                    cb_break+=1
                    if len(ex_break)<18: ex_break.append((gw,pws[i],raw0))
        else:
            passed+=1; outK=bK
        if gK!=bK: e_bert+=1
        if gK!=outK: e_cb+=1
        if gK!=bK:
            errB+=1; keys=set(bykey.keys())
            if not keys: unknown+=1
            else:
                if gK in keys: gold_in+=1
                if len(keys)==1 and gK in keys: gold_unique+=1
                if (bK in keys) and (gK in keys): both+=1
                if bK not in keys: illegal+=1
def pc(x,d): return f"{100*x/max(d,1):.2f}%"
P("="*70)
P(f"كلماتٌ مُقيَّمة: {tot}  [قياسٌ مُحيَّدٌ من كلِّ اصطلاحاتِ CAMeL]")
P("="*70)
P("معدّلُ الخطأِ (صافٍ لغويًّا):")
P(f"  BERT وحدَه          : {e_bert:5d}  ({pc(e_bert,tot)})")
P(f"  CAMeL-أساس + BERT   : {e_cb:5d}  ({pc(e_cb,tot)})   صافٍ {e_bert-e_cb:+d}")
P("-"*70)
P(f"تغطيةُ CAMeL: حسمَ {resolved} ({pc(resolved,tot)})  دقّتُه {pc(r_correct,resolved)}  · لـBERT {passed}")
P(f"حين غيّرَ CAMeL قرارَ BERT: أصلحَ {cb_fix} · أفسدَ {cb_break}  (صافٍ {cb_fix-cb_break:+d})")
P("="*70)
P(f"السقفُ اللغويُّ على أخطاءِ BERT الصافية (إجمالي {errB}):")
P(f"  الذهبيُّ الجائزُ الوحيد (حَسْمٌ يقينيّ) : {gold_unique:5d}  ({pc(gold_unique,errB)})")
P(f"  الذهبيُّ ضمنَ الجائز (بتعدُّد)        : {gold_in:5d}  ({pc(gold_in,errB)})")
P(f"  الصورتان جائزتان معًا                 : {both:5d}  ({pc(both,errB)})")
P(f"  صورةُ BERT غيرُ جائزة                  : {illegal:5d}  ({pc(illegal,errB)})")
P(f"  مجهولةٌ للمحلّل                        : {unknown:5d}  ({pc(unknown,errB)})")
P("="*70)
P("أمثلةٌ أصلحَها CAMeL لغويًّا (الذهبيّ | BERT✗ | حسمُ CAMeL):")
for a,b,c in ex_fix: P(f"   {a:<18} | {b:<18} | {c}")
P("\nأمثلةٌ أفسدَها CAMeL لغويًّا (BERT✔ | CAMeL✗):")
for a,b,c in ex_break: P(f"   {a:<18} | {b:<18} | {c}")
P("="*70)
open(OUT,"w",encoding="utf-8").write(buf.getvalue())
print(f"\n[كُتِبَ إلى {OUT}]")
