# -*- coding: utf-8 -*-
"""diag_ocr_full.py — تشخيصٌ متينٌ لـOCR. المتوسّطُ وحدَه خادعٌ لأنّ صفحةً
منحرفةً واحدةً (runaway) تطغى عليه. لذا نُظهِرُ: الوسيطَ، ونسبةَ الصفحاتِ
المنحرفة (CER>100% أو ناتجٌ أطولُ من ذهبيّه بـ2.5×)، ومتوسّطًا مقصوصًا عند 100%.
الإعداد: معالجة OFF · MAX_SIDE=1600 · المحوّلُ من OCR_LORA. استبعادُ تلوّثِ Tanzil."""
import os, sys, re, collections, statistics
os.environ.setdefault("OCR_PREPROCESS", "0"); os.environ.setdefault("OCR_MAX_SIDE", "1600")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "scripts")); sys.path.insert(0, BASE)
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import ocr_engine as OE
OE.MAX_SIDE = int(os.environ.get("OCR_MAX_SIDE", "1600"))
_STRIP = set(range(0x064B, 0x0653)) | {0x0670, 0x0640} | set(range(0x06D6, 0x06EE))
_LAT = re.compile(r"[A-Za-z]")
def bare(s):
    s = "".join(ch for ch in s if ord(ch) not in _STRIP)
    for a, b in (("أ","ا"),("إ","ا"),("آ","ا"),("ٱ","ا"),("ى","ي"),("ة","ه")): s = s.replace(a, b)
    return s
def is_clean(g):
    g = g.strip()
    return len(g) >= 5 and not _LAT.search(g)
def cer(ref, hyp):
    r, h = list(ref), list(hyp); n, m = len(r), len(h)
    if n == 0: return 0.0 if m == 0 else 1.0
    dp = list(range(m+1))
    for i in range(1, n+1):
        prev = dp[0]; dp[0] = i
        for j in range(1, m+1):
            cur = dp[j]; dp[j] = min(dp[j]+1, dp[j-1]+1, prev+(r[i-1]!=h[j-1])); prev = cur
    return dp[m]/n
def wrecall(ref, hyp):
    rw = collections.Counter(bare(ref).split()); hw = collections.Counter(bare(hyp).split())
    if not rw: return 1.0
    return sum(min(c, hw.get(w, 0)) for w, c in rw.items())/sum(rw.values())
def load(man, root=None):
    rows, sk = [], 0
    for ln in open(man, encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) < 2: continue
        if not is_clean(p[1]): sk += 1; continue
        rows.append((os.path.join(root, p[0]) if root else p[0], p[1].strip()))
    return rows, sk
SETS = [("تراث","data/ocr_classical_pages_test/manifest.tsv","data/ocr_classical_pages_test"),
        ("قرآن","data/ocr_quran_pages_test_root.tsv",None)]
LIMIT = int(os.environ.get("OCR_LIMIT","0"))
print(f"النموذج: {OE.MODEL_ID} · LoRA={os.environ.get('OCR_LORA','(لا شيء!)')} · MAX_SIDE={OE.MAX_SIDE} · MAX_TOKENS={os.environ.get('OCR_MAX_TOKENS','8192')}")
print("="*66)
G = []
for name, man, root in SETS:
    if not os.path.exists(man): print(f"[{name}] مفقود: {man}"); continue
    rows, sk = load(man, root)
    if LIMIT > 0: rows = rows[:LIMIT]
    recs = []; tot = len(rows)
    print(f"  [{name}] معالجة {tot} صفحة ...", flush=True)
    for _i,(path, gold) in enumerate(rows,1):
        try: out = OE.ocr_image(path).strip()
        except Exception as e: print(f"  خطأ {_i}/{tot}:", os.path.basename(path), repr(e)[:50], flush=True); continue
        a = cer(gold, out); b = cer(bare(gold), bare(out)); w = wrecall(gold, out)
        runaway = (a > 1.0) or (len(out) > 2.5*max(1,len(gold)))
        recs.append((a, b, w, len(gold), len(out), runaway, os.path.basename(path), gold, out))
        G.append((a, b, w, runaway))
        print(f"    {_i}/{tot} {os.path.basename(path)}  CER={100*a:.0f}%  len {len(gold)}->{len(out)}{'  <<RUNAWAY' if runaway else ''}", flush=True)
    if not recs: continue
    n = len(recs); cf=[r[0] for r in recs]; cb=[r[1] for r in recs]; wr=[r[2] for r in recs]
    nrun = sum(1 for r in recs if r[5])
    capped = sum(min(x,1.0) for x in cf)/n
    print(f"\n##### {name} — {n} صفحة (استُبعدَ {sk} ملوّثًا) · منحرفة={nrun} ({100*nrun/n:.0f}%) #####")
    print(f"  CER وسيط (median)     = {100*statistics.median(cf):5.2f}%   ← جودةُ الصفحةِ النمطيّة")
    print(f"  CER-حروف وسيط         = {100*statistics.median(cb):5.2f}%")
    print(f"  CER متوسّط مقصوصٌ@100%  = {100*capped:5.2f}%")
    print(f"  CER متوسّط خام         = {100*sum(cf)/n:6.1f}%   (مشوَّهٌ بالمنحرفة)")
    print(f"  استرجاعُ الكلمات وسيط  = {100*statistics.median(wr):5.2f}%")
    recs.sort(key=lambda x: -x[0])
    print(f"  --- أسوأُ 4 (طول ذهبيّ ← ناتج) ---")
    for a,b,w,lg,lo,ru,bn,gold,out in recs[:4]:
        print(f"   • {bn}: CER={100*a:.0f}% · len {lg}->{lo} {'⟵ انحراف' if ru else ''}")
        print(f"     ذ: {gold[:80]}")
        print(f"     ن: {out[:80]}")
    print(f"  --- أفضلُ 3 (صفحاتٌ سليمة) ---")
    for a,b,w,lg,lo,ru,bn,gold,out in sorted(recs,key=lambda x:x[0])[:3]:
        print(f"   • {bn}: CER={100*a:.1f}% · len {lg}->{lo}")
if G:
    n=len(G); cf=[g[0] for g in G]; nrun=sum(1 for g in G if g[3])
    print("\n"+"="*66)
    print(f"الإجماليّ {n} صفحة: وسيط CER={100*statistics.median(cf):.2f}% · مقصوص@100={100*sum(min(x,1.0) for x in cf)/n:.2f}% · منحرفة={nrun} ({100*nrun/n:.0f}%)")
