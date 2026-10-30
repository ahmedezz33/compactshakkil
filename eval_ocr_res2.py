# -*- coding: utf-8 -*-
"""تأكيدٌ مركّز: MAX_SIDE 1600 مقابل 2600 على كلّ الصفحات (OCR_LIMIT=0)، معالجة OFF."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import ocr_engine as OE
os.environ["OCR_PREPROCESS"]="0"
ROOT="data/ocr_classical_pages_test"; MAN=os.path.join(ROOT,"manifest.tsv")
LIMIT=int(os.environ.get("OCR_LIMIT","0"))
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
print(f"صفحات: {len(rows)} · النموذج: {OE.MODEL_ID}")
def run(ms):
    OE.MAX_SIDE=ms; tot=0.0;n=0
    for path,gold in rows:
        try: out=OE.ocr_image(path).strip()
        except Exception as e: print("  خطأ:",os.path.basename(path),repr(e)[:50]); continue
        tot+=cer(gold,out); n+=1
    v=100*tot/max(1,n); print(f"[MAX_SIDE {ms}] CER={v:.2f}%  (صفحات {n})"); return v
a=run(1600); b=run(2600)
print("="*50)
print(f"1600={a:.2f}%  2600={b:.2f}%  الفرق={b-a:+.2f} نقطة")
print("الأفضل:", "1600" if a<b else "2600")
