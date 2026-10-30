# -*- coding: utf-8 -*-
"""قياسُ محرّكِ OCR الفعليّ على الصفحاتِ الكلاسيكيّةِ الذهبيّة، بـCER حقيقيّ.
SWEEP=pre   : معالجةٌ ON مقابل OFF (الافتراضيّ).
SWEEP=res   : مسحُ MAX_SIDE [1600,2000,2600,3200] بمعالجةٍ OFF.
SWEEP=prompt: برومبت EN مقابل AR بمعالجةٍ OFF.
الحدّ: OCR_LIMIT (افتراضي 20؛ 0=الكلّ=61)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),"scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import ocr_engine as OE
ROOT="data/ocr_classical_pages_test"; MAN=os.path.join(ROOT,"manifest.tsv")
LIMIT=int(os.environ.get("OCR_LIMIT","20")); SWEEP=os.environ.get("SWEEP","pre")
def cer(ref,hyp):
    r,h=list(ref),list(hyp); n,m=len(r),len(h)
    if n==0: return 0.0 if m==0 else 1.0
    dp=list(range(m+1))
    for i in range(1,n+1):
        prev=dp[0]; dp[0]=i
        for j in range(1,m+1):
            cur=dp[j]; dp[j]=min(dp[j]+1,dp[j-1]+1,prev+(r[i-1]!=h[j-1])); prev=cur
    return dp[m]/n
rows=[]
for ln in open(MAN,encoding="utf-8"):
    p=ln.rstrip("\n").split("\t")
    if len(p)>=2: rows.append((os.path.join(ROOT,p[0]), p[1].strip()))
if LIMIT>0: rows=rows[:LIMIT]
print(f"صفحات: {len(rows)} · النموذج: {OE.MODEL_ID} · مسح={SWEEP}")
def run(name, preprocess=False, max_side=2600, prompt=None):
    os.environ["OCR_PREPROCESS"]="1" if preprocess else "0"
    OE.MAX_SIDE=max_side
    if prompt is None: os.environ.pop("OCR_PROMPT",None)
    else: os.environ["OCR_PROMPT"]=prompt
    tot=0.0;n=0
    for path,gold in rows:
        try: out=OE.ocr_image(path).strip()
        except Exception as e: print("  خطأ:",os.path.basename(path),repr(e)[:50]); continue
        tot+=cer(gold,out); n+=1
    print(f"[{name}] CER={100*tot/max(1,n):.2f}%  (صفحات {n})")
    return tot/max(1,n)
print("="*56)
res={}
if SWEEP=="pre":
    res["ON"]=run("معالجةٌ ON ",True,2600); res["OFF"]=run("معالجةٌ OFF",False,2600)
elif SWEEP=="res":
    for ms in (1600,2000,2600,3200): res[ms]=run(f"MAX_SIDE {ms}",False,ms)
elif SWEEP=="prompt":
    res["EN"]=run("برومبت EN",False,2600,OE.PROMPT_EN)
    res["AR"]=run("برومبت AR",False,2600,OE.PROMPT_AR)
print("="*56)
best=min(res,key=res.get); print(f"الأفضل: {best}  (CER={100*res[best]:.2f}%)")
