# -*- coding: utf-8 -*-
"""قياسُ دقّةِ الطبقةِ الدلاليّةِ (Ollama) على الكلماتِ الملتبسةِ صوتيًّا، مقابلَ الذهبيّ.
لكلِّ كلمةٍ ملتبسةٍ (فعلٌ بقراءتين+): نُعطي LLM جملةَ BERT + الخيارات، ونقارنُ اختيارَه
بالذهبيّ (اصطلاحٌ محيَّد). نُصنّفُ: أصلحَ (BERT خطأ→LLM صواب) · أفسدَ (BERT صواب→LLM خطأ).
يحتاجُ Ollama يعملُ + النموذجَ مسحوبًا. حدُّ الاستدعاءات SEM_MAX (افتراضي 80)."""
import os, sys, re
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
MAX=int(os.environ.get("SEM_MAX","80"))
import semantic_layer as S
from camel_snap import _norm, _strip
_WAQF=re.compile(r'[ًٌٍَُِ]([اوىي]?)$')
def _conv(s):
    s=_WAQF.sub(r'\1',_norm(s)).replace('ٰ','')
    s=re.sub(r'َ(?=ا)','',s); s=re.sub(r'ِ(?=ي)','',s); s=re.sub(r'ُ(?=و)','',s)
    return s
if not S.enabled():
    print("الطبقةُ غيرُ مفعّلة (لا إعدادات/مفتاح)."); sys.exit(0)
print(f"المحرّك: {S._cfg()['model']} @ {S._cfg()['endpoint']}  (حدُّ الاستدعاءات {MAX})")
gold=[l.rstrip("\n") for l in open("bench_gold.txt",encoding="utf-8")]
pred=[l.rstrip("\n") for l in open("bench_pred_ours.txt",encoding="utf-8")]
calls=0; gold_in=0; fixed=0; broke=0; kept_ok=0; stayed_bad=0
ex_fix=[]; ex_broke=[]
done=False
for g,p in zip(gold,pred):
    if done: break
    gw=g.split(" "); pw=p.split(" ")
    if len(gw)!=len(pw): continue
    for a,b in zip(gw,pw):
        if _strip(a)!=_strip(b): continue
        cands=S.ambiguous(b)
        if len(cands)<2: continue
        if _norm(b) not in {_norm(c) for c in cands}: continue
        if calls>=MAX: done=True; break
        gc=_conv(a); bc=_conv(b); cset={_conv(c) for c in cands}
        chosen=S._ask_llm(p, b, cands); calls+=1
        if chosen is None: continue
        cc=_conv(chosen)
        if gc in cset: gold_in+=1
        if bc!=gc:                       # BERT مخطئٌ هنا
            if cc==gc: fixed+=1; (ex_fix.append((a,b,chosen)) if len(ex_fix)<12 else None)
            else: stayed_bad+=1
        else:                            # BERT مصيبٌ هنا
            if cc!=gc: broke+=1; (ex_broke.append((a,b,chosen)) if len(ex_broke)<12 else None)
            else: kept_ok+=1
net=fixed-broke
print("="*60)
print(f"استدعاءات LLM: {calls}  · الذهبيُّ ضمنَ الخيارات: {gold_in}/{calls}")
print(f"BERT مخطئٌ والطبقةُ أصلحَتْ : {fixed}")
print(f"BERT مخطئٌ وبقيَ خطأً       : {stayed_bad}")
print(f"BERT مصيبٌ والطبقةُ أفسدَتْ : {broke}   ← يجبُ أن يكونَ صغيرًا جدًّا")
print(f"BERT مصيبٌ وبقيَ صوابًا     : {kept_ok}")
print(f"الأثرُ الصافي: {net:+d}")
print("="*60)
if ex_fix:
    print("أصلحَتْ (الذهبيّ | BERT✗ | اختيارُ LLM):")
    for a,b,c in ex_fix: print(f"   {a} | {b} | {c}")
if ex_broke:
    print("\nأفسدَتْ (الذهبيّ | BERT✔ | اختيارُ LLM):")
    for a,b,c in ex_broke: print(f"   {a} | {b} | {c}")
print("="*60)
