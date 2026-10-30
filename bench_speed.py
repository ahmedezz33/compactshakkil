# -*- coding: utf-8 -*-
"""مقياسُ السرعة: يُثبِتُ أنّ diacritize_batch == diacritize (سطرًا سطرًا) ويقيسُ التسارع.
شغّلْ عاديًّا (fp32)، أو  set GRAFT_FP16=1  لقياسِ نصفِ الدقّة (يُقارَنُ معه عددُ الاختلافات)."""
import sys, os, time
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
N=int(os.environ.get("N","300")); BS=int(os.environ.get("BS","16"))
import sys as _s2, os as _o2
_s2.path.insert(0, _o2.path.join(_o2.path.dirname(_o2.path.abspath(__file__)),'scripts'))
from bert_graft_infer import GraftInfer
INF=GraftInfer()
lines=[l.strip() for l in open("bench_bare.txt",encoding="utf-8") if l.strip()][:N]
print(f"أسطر: {len(lines)} · حجمُ الدفعة: {BS} · fp16={os.environ.get('GRAFT_FP16')=='1'}")
# إحماء
INF._diac_one(lines[0]); INF.diacritize_batch(lines[:2])
t0=time.time(); single=[INF._diac_one(l) for l in lines]; t1=time.time()
batch=[]
for i in range(0,len(lines),BS): batch+=INF.diacritize_batch(lines[i:i+BS])
t2=time.time()
mis=sum(1 for a,b in zip(single,batch) if a!=b)
print("="*52)
print(f"سطرًا‑سطرًا : {t1-t0:6.2f}s  ({(t1-t0)/len(lines)*1000:.1f} ms/سطر)")
print(f"تجميعًا     : {t2-t1:6.2f}s  ({(t2-t1)/len(lines)*1000:.1f} ms/سطر)")
print(f"التسارع     : ×{(t1-t0)/max(t2-t1,1e-9):.2f}")
print(f"اختلافاتٌ بين الطريقتين: {mis}  ← يجبُ أن يكونَ صفرًا (fp32)")
print("="*52)
if mis:
    for a,b in zip(single,batch):
        if a!=b: print("  مثال:\n   single:",a[:80],"\n   batch :",b[:80]); break
