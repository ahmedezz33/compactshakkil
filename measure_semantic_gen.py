# -*- coding: utf-8 -*-
"""قياسُ متغيّرِ «التوليدِ الحرّ»: Qwen يُشكّلُ الكلمةَ الملتبسةَ بنفسِه (لا اختيارٌ من CAMeL)،
مقيَّدًا بنفسِ الرسمِ (نرفضُ أيَّ صورةٍ تغيّرُ الحروف). نقيسُ أصلح/أفسد مقابلَ الذهبيّ.
الكاشفُ نفسُه (فعلٌ بزوجِ معلوم/مجهول لدى CAMeL) حتى تبقى الكلفةُ محدودة. يحتاجُ Ollama."""
import os, sys, re, json, urllib.request
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
_AR=re.compile(r'[ء-ْ]+')
CFG=S._cfg(); EP=CFG["endpoint"]; MODEL=CFG["model"]; TMO=max(CFG.get("timeout",30),60)
def _gen(sentence, bare):
    sysp=("أنت مشكِّلٌ عربيٌّ خبير. تُعيدُ الكلمةَ المطلوبةَ مشكَّلةً تشكيلًا كاملًا صحيحًا حسبَ "
          "معناها في الجملة، بنفسِ حروفِها تمامًا دون زيادةٍ أو نقص. أجبْ بالكلمةِ وحدَها لا غير.")
    usrp=(f"الجملة: {sentence}\n\nشكّلِ الكلمةَ: «{bare}» "
          f"(فعلٌ، قد يكونُ معلومًا أو مجهولًا بحسبِ السياق). أعطِ صورتَها المشكّلةَ كاملةً فقط.")
    body=json.dumps({"model":MODEL,"temperature":0,"stream":False,
        "messages":[{"role":"system","content":sysp},{"role":"user","content":usrp}]}).encode("utf-8")
    try:
        req=urllib.request.Request(EP,data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=TMO) as r:
            out=json.loads(r.read().decode("utf-8"))
        txt=out["choices"][0]["message"]["content"].strip()
        for tok in _AR.findall(txt):
            if _strip(tok)==bare: return tok      # نفسُ الرسمِ ← مقبول
        return None
    except Exception as e:
        print("gen skip:",e); return None
# تسخينُ النموذج (تفادي مهلةِ أوّلِ تحميل)
try: _gen("تهيئة","قال")
except Exception: pass
gold=[l.rstrip("\n") for l in open("bench_gold.txt",encoding="utf-8")]
pred=[l.rstrip("\n") for l in open("bench_pred_ours.txt",encoding="utf-8")]
calls=0; fix=0; broke=0; stay=0; keep=0; reject=0; done=False
ex_fix=[]; ex_broke=[]
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
        gen=_gen(p,_strip(b)); calls+=1
        if gen is None: reject+=1; continue
        gc=_conv(a); bc=_conv(b); nc=_conv(gen)
        if bc!=gc:
            if nc==gc: fix+=1; (ex_fix.append((a,b,gen)) if len(ex_fix)<15 else None)
            else: stay+=1
        else:
            if nc!=gc: broke+=1; (ex_broke.append((a,b,gen)) if len(ex_broke)<15 else None)
            else: keep+=1
print("="*60)
print(f"المحرّك: {MODEL} (توليدٌ حرّ، تقييدُ الرسم) · استدعاءات: {calls} · مرفوض(رسم مختلف/فشل): {reject}")
print(f"BERT مخطئٌ والتوليدُ أصلحَ : {fix}")
print(f"BERT مخطئٌ وبقيَ خطأً     : {stay}")
print(f"BERT مصيبٌ والتوليدُ أفسدَ : {broke}   ← يجبُ أن يكونَ صغيرًا جدًّا")
print(f"BERT مصيبٌ وبقيَ صوابًا   : {keep}")
print(f"الأثرُ الصافي: {fix-broke:+d}")
print("="*60)
if ex_fix:
    print("أصلحَ (الذهبيّ | BERT✗ | توليدُ Qwen):")
    for a,b,c in ex_fix: print(f"   {a} | {b} | {c}")
if ex_broke:
    print("\nأفسدَ (الذهبيّ | BERT✔ | توليدُ Qwen):")
    for a,b,c in ex_broke: print(f"   {a} | {b} | {c}")
print("="*60)
