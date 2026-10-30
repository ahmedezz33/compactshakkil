# -*- coding: utf-8 -*-
"""diag_ocr_errors.py — يفكّكُ خطأَ OCR إلى ثلاثةِ أنواع (بلا تدريب):
  1) CER كامل          : الخطأُ الكلّيّ كما يراه المقياس.
  2) CER مجرّدٌ من الحركات: يُجرَّدُ التشكيلُ من الطرفين → يعزلُ خطأَ *الحروف*.
  3) استرجاعُ الكلماتِ المجرّدة: نسبةُ كلماتِ الذهبيِّ المجرّدةِ الموجودةِ في الناتج (multiset)
     → عالٍ = الحروفُ تُقرأُ لكنّ الترتيب/المقياس هو المشكلة؛ منخفضٌ = حذفٌ/عجزٌ حقيقيّ.
الحدّ: OCR_LIMIT (افتراضي 20؛ 0=الكلّ=61). المعالجةُ OFF، البرومبت الافتراضيّ (AR)."""
import os, sys, re, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),"scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import ocr_engine as OE
os.environ["OCR_PREPROCESS"]="0"
ROOT="data/ocr_classical_pages_test"; MAN=os.path.join(ROOT,"manifest.tsv")
LIMIT=int(os.environ.get("OCR_LIMIT","20"))
# حركات + ألف خنجريّة + تطويل + رموز وقف
_STRIP=set(range(0x064B,0x0653))|{0x0670,0x0640}|set(range(0x06D6,0x06EE))
def bare(s):
    s="".join(ch for ch in s if ord(ch) not in _STRIP)
    for a,b in (("أ","ا"),("إ","ا"),("آ","ا"),("ٱ","ا"),("ى","ي"),("ة","ه")): s=s.replace(a,b)
    return s
def cer(ref,hyp):
    r,h=list(ref),list(hyp); n,m=len(r),len(h)
    if n==0: return 0.0 if m==0 else 1.0
    dp=list(range(m+1))
    for i in range(1,n+1):
        prev=dp[0]; dp[0]=i
        for j in range(1,m+1):
            cur=dp[j]; dp[j]=min(dp[j]+1,dp[j-1]+1,prev+(r[i-1]!=h[j-1])); prev=cur
    return dp[m]/n
def wrecall(ref,hyp):
    rw=collections.Counter(bare(ref).split()); hw=collections.Counter(bare(hyp).split())
    if not rw: return 1.0
    hit=sum(min(c,hw.get(w,0)) for w,c in rw.items())
    return hit/sum(rw.values())
rows=[]
for ln in open(MAN,encoding="utf-8"):
    p=ln.rstrip("\n").split("\t")
    if len(p)>=2: rows.append((os.path.join(ROOT,p[0]), p[1].strip()))
if LIMIT>0: rows=rows[:LIMIT]
print(f"صفحات: {len(rows)} · النموذج: {OE.MODEL_ID} · معالجة=OFF")
print("="*60)
cf=cb=wr=0.0; n=0
for i,(path,gold) in enumerate(rows):
    try: out=OE.ocr_image(path).strip()
    except Exception as e: print("  خطأ:",os.path.basename(path),repr(e)[:50]); continue
    a=cer(gold,out); b=cer(bare(gold),bare(out)); w=wrecall(gold,out)
    cf+=a; cb+=b; wr+=w; n+=1
    if i<3:
        print(f"\n--- صفحة {os.path.basename(path)} ---")
        print("ذهبيّ[:180]:", gold[:180])
        print("ناتج[:180] :", out[:180])
        print(f"CER={100*a:.1f}%  CER-مجرّد={100*b:.1f}%  استرجاع-كلمات={100*w:.1f}%  (طول ذهبيّ {len(gold)} ناتج {len(out)})")
print("\n"+"="*60)
print(f"المتوسّط على {n} صفحة:")
print(f"  CER كامل            = {100*cf/max(1,n):.2f}%")
print(f"  CER مجرّدٌ من الحركات = {100*cb/max(1,n):.2f}%   ← خطأُ الحروف وحدَها")
print(f"  استرجاعُ الكلمات     = {100*wr/max(1,n):.2f}%   ← 100%=لا حذف/عجز، المشكلة ترتيب/حركات")
