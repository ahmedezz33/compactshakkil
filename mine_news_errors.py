# -*- coding: utf-8 -*-
"""تعدينٌ دقيق: يُشغّلُ BERT على أخبارِك الذهبيّةِ ويلتقطُ الكلماتِ التي يُخطئُها،
مرتّبةً بالتكرارِ مع صورتِها الذهبيّةِ ووسمِها المعجميّ — مرشّحاتُ القاموسِ المستحقّة.
يستعملُ diacritize_batch (سريع). المخرجُ: news_error_candidates.json + طباعة."""
import sys, os, json, collections, re, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),"scripts"))
for _s in (sys.stdout,sys.stderr):
    try: _s.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
HAR=set("ًٌٍَُِّْٰ")
def strip(s): return "".join(c for c in s if c not in HAR)
_map=str.maketrans("أإآٱىة","اااايه")
def _norm(s): return "".join(c for c in s if c not in {"ّ","ْ"}).translate(_map)
def internally_bare(w):
    L=[];M=[]
    for ch in w:
        if ch in HAR:
            if M:M[-1]+=ch
        else:L.append(ch);M.append("")
    for i in range(1,len(L)-1):
        if M[i]=="": return True
    return False
con=sqlite3.connect("lexicon/arabic_lexicon.db"); pc={}
def pos(b):
    if b in pc: return pc[b]
    try:
        r=con.execute("SELECT analyses_json FROM words WHERE word=? LIMIT 1",(b,)).fetchone()
        p=frozenset(a.get("pos","") for a in json.loads(r[0])) if r and r[0] else frozenset()
    except Exception: p=frozenset()
    pc[b]=p; return p
from bert_graft_infer import GraftInfer
INF=GraftInfer()
exist={strip(k) for k in json.load(open("name_overrides.json",encoding="utf-8")) if not k.startswith("_")}
exist|={strip(k) for k in json.load(open("fixed_forms.json",encoding="utf-8")) if not k.startswith("_")}
lines=[l.strip() for l in open("data/news_gold_clean.txt",encoding="utf-8") if l.strip()]
N=int(os.environ.get("N","0"))
if N>0: lines=lines[:N]
err=collections.defaultdict(collections.Counter)      # bare -> {gold_form: count}
bert_eg={}
BS=32
for i in range(0,len(lines),BS):
    chunk=lines[i:i+BS]
    preds=INF.diacritize_batch([strip(l) for l in chunk])
    for gold,pred in zip(chunk,preds):
        gw=gold.split(" "); pw=pred.split(" ")
        if len(gw)!=len(pw): continue
        for a,b in zip(gw,pw):
            if strip(a)!=strip(b): continue
            if _norm(a)!=_norm(b):                     # خطأُ BERT حقيقيّ
                bare=strip(a)
                if bare in exist or len(bare)<3: continue
                if internally_bare(a): continue        # ذهبيٌّ ناقصٌ ← تجاهل
                err[bare][a]+=1; bert_eg[bare]=b
cand=[]
for bare,c in err.items():
    tot=sum(c.values()); top,tn=c.most_common(1)[0]
    if tot>=2 and tn/tot>=0.8:
        p=pos(bare); tag=("علم" if ("noun_prop" in p and "verb" not in p) else
                          "مجهول" if not p else "/".join(sorted(p))[:18])
        cand.append((tot,bare,top,bert_eg[bare],tag))
cand.sort(reverse=True)
print(f"كلماتٌ يُخطئُها BERT في الأخبار (متكرّرة، صورةٌ ذهبيّةٌ ثابتة): {len(cand)}")
print("="*66)
print(f"  {'×':>3}  {'الذهبيّ':<16} | {'BERT✗':<16} | الوسم")
out={}
for tot,bare,top,be,tag in cand[:60]:
    print(f"  {tot:>3}  {top:<16} | {be:<16} | {tag}")
    out[bare]=top
json.dump(out, open("news_error_candidates.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("="*66)
print(f"حُفِظَ {len(out)} في news_error_candidates.json")
print("راجِعْها: أضِفِ الأعلامَ الحقيقيّةَ إلى name_overrides.json")
