# -*- coding: utf-8 -*-
"""التقييمُ الكامل: الذهبيّ | BERT | CAMeL لكلِّ حالة.
يقيسُ BERT وCAMeL (اختيارَ MLE الأعلى) مقابلَ الذهبيّ كلمةً كلمة (اصطلاحٌ موحَّد)،
ويسردُ لكلِّ فئةٍ صفوفًا ثلاثيّةً (الذهبيّ | بيرت | كامل). يكتبُ التقريرَ كاملًا إلى eval_report.txt."""
import sys, os, random, re, io, functools
N=int(os.environ.get("BENCH_N","3000"))       # 0 = كلّ الملفّ
EX=int(os.environ.get("EX","4000"))           # أقصى عددِ صفوفٍ تُكتبُ لكلِّ فئة
OUT=os.environ.get("EVAL_OUT","eval_report.txt")
buf=io.StringIO()
def P(*a):
    s=" ".join(str(x) for x in a); print(s); buf.write(s+"\n")
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

P(f"… تحميل BERT + CAMeL + MLE (عيّنة={'الكلّ' if N==0 else N})")
import app_teach as A
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.disambig.mle import MLEDisambiguator
from camel_snap import _norm, _strip
from data.vocab_v2 import strip_diacritics, split_letters_and_diacritics
an=Analyzer(MorphologyDB.builtin_db())
mle=MLEDisambiguator.pretrained()

_DIAC=set("ًٌٍَُِّْٰ"); _TST=set("ًٌٍّْٰ")
def _letters(s): return "".join(c for c in s if c not in _DIAC)
def _rasm(s): return _norm(_letters(s))
def _novowel(s): return _norm("".join(c for c in s if c not in _TST))
def _nonar(s): return bool(re.search(r"[^؀-ۿ]", s))
@functools.lru_cache(maxsize=300000)
def _has_any(bare):
    try: return bool(an.analyze(bare))
    except Exception: return False

def camel_err_kind(gw,cw,had):
    if _nonar(gw) or _nonar(cw): return "ترقيم/رمز"
    if not had: return "مجهولةٌ لـCAMeL (علم/أجنبيّ)"
    if _rasm(gw)==_rasm(cw):
        if _novowel(gw)==_novowel(cw): return "اصطلاح (تنوين/شدّة/سكون)"
        try:
            Lg,Dg=split_letters_and_diacritics(_norm(gw)); Lc,Dc=split_letters_and_diacritics(_norm(cw))
            if len(Dg)==len(Dc):
                diffs=[i for i in range(len(Dg)) if Dg[i]!=Dc[i]]
                if diffs and all(i==len(Dg)-1 for i in diffs): return "حركةُ آخِرٍ خاطئة (إعراب)"
                return "حركةٌ داخليّةٌ خاطئة (بنية)"
        except Exception: pass
        return "حركةٌ مختلفة"
    return "رسمٌ مختلف"

lines=[l.strip() for l in open("data/processed/test.txt",encoding="utf-8") if l.strip()]
random.Random(13).shuffle(lines)
if N>0: lines=lines[:N]

tot=0; bert_err=0; camel_err=0
both_ok=0; bok_cbad=0; bbad_cok=0; both_bad=0
dmg_by={}; help_rows=[]; bothbad_rows=[]
skipped=0; nlines=0
for gold in lines:
    gws=gold.split(" "); bare=[_strip(w) for w in gws]
    pb=A.INF.diacritize(strip_diacritics(gold)); pws=pb.split(" ")
    if len(pws)!=len(gws): skipped+=1; continue
    try:
        dis=mle.disambiguate(bare)
        cws=[(d.analyses[0].analysis['diac'] if d.analyses else bare[i]) for i,d in enumerate(dis)]
    except Exception:
        skipped+=1; continue
    if len(cws)!=len(gws): skipped+=1; continue
    nlines+=1; tot+=len(gws)
    for i,gw in enumerate(gws):
        g=_norm(gw); b=_norm(pws[i]); c=_norm(cws[i])
        be=(b!=g); ce=(c!=g)
        if be: bert_err+=1
        if ce: camel_err+=1
        if not be and not ce: both_ok+=1
        elif not be and ce:
            bok_cbad+=1; k=camel_err_kind(gw,cws[i],_has_any(bare[i]))
            dmg_by.setdefault(k,[])
            if len(dmg_by[k])<EX: dmg_by[k].append((gw,pws[i],cws[i]))
        elif be and not ce:
            bbad_cok+=1
            if len(help_rows)<EX: help_rows.append((gw,pws[i],cws[i]))
        else:
            both_bad+=1
            if len(bothbad_rows)<EX: bothbad_rows.append((gw,pws[i],cws[i]))

def pc(x,d): return f"{100*x/max(d,1):.2f}%"
def rows(title, lst):
    P(f"\n── {title}  (مكتوبٌ منها {len(lst)}) ──")
    P(f"   {'الذهبيّ':<22} | {'BERT':<22} | {'CAMeL':<22}")
    for gw,bw,cw in lst:
        P(f"   {gw:<22} | {bw:<22} | {cw:<22}")

P("="*70)
P(f"أسطرٌ مُقيَّمة: {nlines}  (متجاوَزة: {skipped})   كلماتٌ: {tot}")
P("معدّلُ الخطأِ على الكلمة (موحَّد):  BERT {0} ({1})   |   CAMeL {2} ({3})".format(
    bert_err,pc(bert_err,tot),camel_err,pc(camel_err,tot)))
P("="*70)
P("المقارنةُ خلية‑بخلية:")
P(f"  كلاهما صحيح            : {both_ok:6d}  ({pc(both_ok,tot)})")
P(f"  BERT صحيح / CAMeL خاطئ : {bok_cbad:6d}  ({pc(bok_cbad,tot)})  ← CAMeL يُفسِدُها")
P(f"  BERT خاطئ / CAMeL صحيح : {bbad_cok:6d}  ({pc(bbad_cok,tot)})  ← CAMeL يُصلِحُها")
P(f"  كلاهما خاطئ            : {both_bad:6d}  ({pc(both_bad,tot)})")
net=bbad_cok-bok_cbad
P(f"  الأثرُ الصافي لو استبدلنا بـCAMeL = {bbad_cok} − {bok_cbad} = {net:+d} كلمة  (سالبٌ = CAMeL أسوأ)")
P("="*70)
P("فين خطأ CAMeL؟ تصنيفُ «BERT صحيح / CAMeL خاطئ»:")
for k,v in sorted(dmg_by.items(), key=lambda kv:-len(kv[1])):
    P(f"  {k:<28}: {len(v)}")
P("="*70)
P("القوائمُ الكاملة — الذهبيّ | BERT | CAMeL")
for k,v in sorted(dmg_by.items(), key=lambda kv:-len(kv[1])):
    rows(f"[CAMeL يُفسِد] {k}", v)
rows("[CAMeL يُصلِح] BERT خاطئ / CAMeL صحيح", help_rows)
rows("[كلاهما خاطئ]", bothbad_rows)
P("="*70)
with open(OUT,"w",encoding="utf-8") as f: f.write(buf.getvalue())
print(f"\n[كُتِبَ التقريرُ إلى {OUT}]  (أسطر: {buf.getvalue().count(chr(10))})")
